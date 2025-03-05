#!/usr/bin/env python3

import os
import time
import logging
from pythonjsonlogger.json import JsonFormatter
import obd
from obd import commands

# Optional: for storing data in InfluxDB
from influxdb_client import InfluxDBClient, Point, WritePrecision

###############################################################################
# CONFIGURE LOGGER (Printing JSON to stdout)
###############################################################################
logger = logging.getLogger("obd_logger")
logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
formatter = JsonFormatter()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

###############################################################################
# INFLUX CONFIG
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
# ASYNC CALLBACK
###############################################################################
def async_callback(response):
    """
    Logs each new async reading. If the response is null, logs None.
    Also writes data to Influx if you'd like.
    """
    cmd_name = response.command.name if response.command else "UnknownCommand"
    if response.is_null():
        logger.info({"event": "async_snapshot", "command": cmd_name, "value": None})
        return

    val = response.value
    if hasattr(val, "to_tuple"):
        val_tuple = val.to_tuple()
        logger.info({"event": "async_snapshot", "command": cmd_name, "value": val_tuple})

        # Example: write numeric + unit to Influx
        numeric_value = val_tuple[0]
        unit = None
        if len(val_tuple) > 1 and val_tuple[1]:
            if len(val_tuple[1][0]) > 0:
                unit = val_tuple[1][0][0]
        fields = {"value": numeric_value}
        if unit:
            fields["unit"] = unit
        tags = {"command": cmd_name}
        write_influx("obd_async", fields, tags)
    else:
        val_str = str(val)
        logger.info({"event": "async_snapshot", "command": cmd_name, "value": val_str})
        # If storing strings:
        fields = {"value_str": val_str}
        tags = {"command": cmd_name}
        write_influx("obd_async", fields, tags)

###############################################################################
# MAIN SCRIPT
###############################################################################
def main():
    logger.info({"event": "startup", "message": "OBD app launched. Will run continuously."})

    static_commands = [
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.RPM,
        commands.SPEED,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS
    ]
    async_commands = static_commands  # same set, or you can change

    # Outer loop: keep trying to connect forever
    while True:
        try:
            # 1) Try to connect (blocking)
            logger.info({"event": "attempt_connection", "message": "Trying to connect to OBD..."})
            connection = obd.OBD(portstr="/dev/ttyUSB0", fast=False, timeout=1.0)
            if not connection.is_connected():
                logger.error({
                    "event": "connection_failure",
                    "message": "Could not connect (static). Will retry."
                })
                connection.close()
                time.sleep(5)
                continue  # go back to while True to try again

            logger.info({"event": "connection_success", "message": "OBD-II connected (static)"})

            # 2) STATIC QUERIES
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

            # Write static to Influx
            fields = {}
            for k, v in static_data.items():
                if v is None:
                    continue
                if isinstance(v, tuple):
                    numeric_value = v[0]
                    unit = None
                    if len(v) > 1 and v[1]:
                        if len(v[1][0]) > 0:
                            unit = v[1][0][0]
                    fields[k] = numeric_value
                    if unit:
                        fields[k + "_unit"] = unit
                else:
                    fields[k + "_str"] = v
            if fields:
                write_influx("obd_static", fields)

            connection.close()
            time.sleep(0.03125)  # small delay for adapter

            # 3) ASYNC connection
            async_connection = obd.Async(
                portstr="/dev/ttyUSB0",
                fast=False,
                timeout=0.015625,
                delay_cmds=0.0078125
            )
            if not async_connection.is_connected():
                logger.error({
                    "event": "connection_failure",
                    "message": "Could not connect (async). Will retry."
                })
                async_connection.close()
                time.sleep(5)
                continue

            logger.info({"event": "connection_success", "message": "OBD-II connected (async)"})

            with async_connection.paused():
                for cmd in async_commands:
                    if cmd in async_connection.supported_commands:
                        async_connection.watch(cmd, callback=async_callback)
                    else:
                        logger.info({"event": "unsupported_command", "command": cmd.name})

            async_connection.start()

            logger.info({"event": "async_loop_started", "message": "OBD reading indefinitely..."})

            # 4) Wait for disconnection or user break
            while True:
                # If physically disconnected, the library may no longer be is_connected
                if not async_connection.is_connected():
                    logger.warning({"event": "async_disconnected", "message": "OBD lost connection."})
                    break
                time.sleep(5)

            # 5) Clean up
            async_connection.stop()
            async_connection.close()
            logger.info({"event": "async_connection_stopped"})

            # Try reconnecting after a delay
            logger.info({"event": "attempt_reconnect", "message": "Will attempt to reconnect soon..."})
            time.sleep(5)

        except KeyboardInterrupt:
            # If the user explicitly kills the container/script
            logger.info({"event": "shutdown_requested", "message": "Ctrl+C received, exiting."})
            break
        except Exception as e:
            logger.exception({"event": "unhandled_exception", "error": str(e)})
            # Try again after a delay
            time.sleep(5)
            # continue the loop to keep trying

    logger.info({"event": "finished_obd_test", "message": "Exiting main loop."})

if __name__ == "__main__":
    main()