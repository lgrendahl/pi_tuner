#!/usr/bin/env python3

import os
import time
import logging
from pythonjsonlogger.json import JsonFormatter
import obd
from obd import commands

# InfluxDB client (if you're writing to Influx)
from influxdb_client import InfluxDBClient, Point, WritePrecision

###############################################################################
# CONFIGURE LOGGER (prints JSON to stdout)
###############################################################################
logger = logging.getLogger("obd_logger")
logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
formatter = JsonFormatter()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

###############################################################################
# INFLUX CONFIG & CLIENT (if needed)
###############################################################################
INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "my-token")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "my-org")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "obd_data")

influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api()

def write_influx(measurement, fields, tags=None):
    if tags is None:
        tags = {}
    point = Point(measurement)
    for k, v in tags.items():
        point.tag(k, v)
    for k, v in fields.items():
        if v is not None:
            point.field(k, v)
    write_api.write(bucket=INFLUX_BUCKET, record=point, write_precision=WritePrecision.NS)

###############################################################################
# CAR-STOP DETECTION LOGIC
###############################################################################
ZERO_RPM_THRESHOLD = 30  # how many consecutive zero-RPM snapshots = "stopped"
zero_rpm_count = 0
car_stopped = False

def check_if_engine_off(cmd, val_tuple):
    """
    If `cmd` is RPM and val_tuple[0] is near zero for many snapshots in a row,
    we consider the engine off. Returns True if we should stop the app.
    """
    global zero_rpm_count, car_stopped

    # Only track if cmd == "RPM" and we have a numeric value
    if cmd == "RPM" and isinstance(val_tuple, tuple):
        numeric_value = val_tuple[0]
        # If numeric_value is "small enough" to consider 0 (some cars idle ~700-800)
        # We'll treat anything < 10 as effectively 0.
        if numeric_value is not None and numeric_value < 10:
            zero_rpm_count += 1
        else:
            zero_rpm_count = 0

    # If we exceed consecutive threshold, we'll consider the engine off
    if zero_rpm_count >= ZERO_RPM_THRESHOLD:
        car_stopped = True
        logger.info({"event": "car_stopped", "reason": "rpm_zero_threshold_reached"})
        return True

    return False

###############################################################################
# ASYNC CALLBACK
###############################################################################
def async_callback(response):
    """
    Logs each new async reading (continuously).
    If the response is null, logs None.
    Also attempts to detect if the engine is off.
    """
    cmd_name = response.command.name if response.command else "UnknownCommand"
    if response.is_null():
        logger.info({"event": "async_snapshot", "command": cmd_name, "value": None})
        return

    val = response.value
    if hasattr(val, "to_tuple"):
        val_tuple = val.to_tuple()  # e.g. (rpm_value, [["revolutions_per_minute", 1]])
        logger.info({"event": "async_snapshot", "command": cmd_name, "value": val_tuple})

        # Optionally write to Influx
        if len(val_tuple) > 0:
            numeric_value = val_tuple[0]
            # Attempt to parse the unit
            unit = None
            if len(val_tuple) > 1 and val_tuple[1]:
                if len(val_tuple[1][0]) > 0:
                    unit = val_tuple[1][0][0]
            fields = {"value": numeric_value}
            if unit:
                fields["unit"] = unit
            tags = {"command": cmd_name}
            write_influx("obd_async", fields, tags)

        # Check if engine is off
        if check_if_engine_off(cmd_name, val_tuple):
            # If engine is considered off, we can signal the main loop to exit
            # (We won't explicitly stop the async loop here, the main loop will handle it)
            pass

    else:
        # It's a string or something else
        val_str = str(val)
        logger.info({"event": "async_snapshot", "command": cmd_name, "value": val_str})
        # Influx write as string (optional):
        fields = {"value_str": val_str}
        tags = {"command": cmd_name}
        write_influx("obd_async", fields, tags)

###############################################################################
# MAIN SCRIPT
###############################################################################
def main():
    logger.info({"event": "starting_obd_test"})

    ############################################################################
    # 1) STATIC (SYNCHRONOUS) QUERIES
    ############################################################################
    static_commands = [
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.RPM,
        commands.SPEED,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS
    ]

    connection = obd.OBD(portstr="/dev/ttyUSB0", fast=False, timeout=1.0)

    if connection.is_connected():
        logger.info({"event": "connection_success", "message": "OBD-II connected (static)"})
    else:
        logger.error({"event": "connection_failure", "message": "Could not connect (static)"})
        return

    # Gather static data
    static_data = {}
    for cmd in static_commands:
        if cmd in connection.supported_commands:
            resp = connection.query(cmd)
            if resp.is_null():
                static_data[cmd.name] = None
            else:
                val = resp.value
                if hasattr(val, "to_tuple"):
                    val = val.to_tuple()
                else:
                    val = str(val)
                static_data[cmd.name] = val
        else:
            static_data[cmd.name] = None

    logger.info({"event": "static_obd_snapshot", "data": static_data})
    # Optionally write static data to Influx
    fields_to_write = {}
    for k, v in static_data.items():
        if v is None:
            continue
        if isinstance(v, tuple):
            numeric_value = v[0]
            unit = None
            if len(v) > 1 and v[1]:
                if len(v[1][0]) > 0:
                    unit = v[1][0][0]
            fields_to_write[k] = numeric_value
            if unit:
                fields_to_write[k + "_unit"] = unit
        else:
            fields_to_write[k + "_str"] = v
    if fields_to_write:
        write_influx("obd_static", fields_to_write)

    connection.close()
    time.sleep(0.03125)

    ############################################################################
    # 2) ASYNC (RUNS CONTINUOUSLY UNTIL CAR STOPS OR Ctrl+C)
    ############################################################################
    async_cmds = [
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.RPM,
        commands.SPEED,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS
    ]

    async_connection = obd.Async(
        portstr="/dev/ttyUSB0",
        fast=False,
        timeout=0.015625,
        delay_cmds=0.0078125
    )

    if not async_connection.is_connected():
        logger.error({"event": "connection_failure", "message": "Could not connect (async)"})
        return

    logger.info({"event": "connection_success", "message": "OBD-II connected (async)"})

    with async_connection.paused():
        for cmd in async_cmds:
            if cmd in async_connection.supported_commands:
                async_connection.watch(cmd, callback=async_callback)
            else:
                logger.info({"event": "unsupported_command", "command": cmd.name})

    async_connection.start()

    # Main loop: run until we decide the car is off (car_stopped) or Ctrl+C
    try:
        while True:
            if car_stopped:
                logger.info({"event": "exiting", "reason": "car_stopped"})
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info({"event": "shutdown_requested"})
    finally:
        async_connection.stop()
        logger.info({"event": "async_connection_stopped"})

    logger.info({"event": "finished_obd_test"})

if __name__ == "__main__":
    main()