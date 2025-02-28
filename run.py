#!/usr/bin/env python3

import time
import logging
from pythonjsonlogger import jsonlogger
import obd
from obd import commands

logger = logging.getLogger("obd_logger")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("app.log")
# No indentation -> single-line JSON
formatter = jsonlogger.JsonFormatter()
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

###############################################################################
# ASYNC CALLBACK for certain commands
###############################################################################
def async_callback(response):
    """
    Invoked whenever the async connection receives new data for a watched PID.
    Logs the result (or None if it's null).
    """
    cmd_name = response.command.name if response.command else "UnknownCommand"
    if response.is_null():
        logger.info({
            "event": "async_snapshot",
            "command": cmd_name,
            "value": None
        })
        return

    val = response.value
    # If numeric, val might support .to_tuple()
    if hasattr(val, "to_tuple"):
        val = val.to_tuple()
    else:
        # For bit arrays, strings, etc.
        val = str(val)

    logger.info({
        "event": "async_snapshot",
        "command": cmd_name,
        "value": val
    })

def main():
    logger.info({"event": "starting_obd_test"})

    ############################################################################
    # 1) Static OBD Connection & Queries
    ############################################################################
    connection = obd.OBD(portstr="/dev/ttyUSB0")

    if connection.is_connected():
        logger.info({"event": "connection_success", "message": "OBD-II connected (static)"})
    else:
        logger.error({"event": "connection_failure", "message": "Could not connect (static)"})
        return

    # Full list of commands to query once
    test_commands = [
        commands.RPM,
        commands.SPEED,
        commands.COOLANT_TEMP,
        commands.PIDS_A,
        commands.STATUS,
        commands.FREEZE_DTC,
        commands.FUEL_STATUS,
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.SHORT_FUEL_TRIM_1,
        commands.LONG_FUEL_TRIM_1,
        commands.SHORT_FUEL_TRIM_2,
        commands.LONG_FUEL_TRIM_2,
        commands.FUEL_PRESSURE,
        commands.INTAKE_PRESSURE,
        commands.RPM,
        commands.SPEED,
        commands.TIMING_ADVANCE,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS,
        commands.AIR_STATUS,
        commands.O2_SENSORS,
        commands.O2_B1S1,
        commands.O2_B1S2,
        commands.O2_B1S3,
        commands.O2_B1S4,
        commands.O2_B2S1,
        commands.O2_B2S2,
        commands.O2_B2S3,
        commands.O2_B2S4,
        commands.OBD_COMPLIANCE,
        commands.O2_SENSORS_ALT,
        commands.AUX_INPUT_STATUS,
        commands.RUN_TIME,
        commands.PIDS_B,
        commands.DISTANCE_W_MIL,
        commands.FUEL_RAIL_PRESSURE_VAC,
        commands.FUEL_RAIL_PRESSURE_DIRECT,
        commands.FUEL_LEVEL,
        commands.ETHANOL_PERCENT,
        commands.EVAP_VAPOR_PRESSURE_ABS,
        commands.EVAP_VAPOR_PRESSURE_ALT,
        commands.OIL_TEMP,
        commands.FUEL_INJECT_TIMING
    ]

    log_data = {}
    for cmd in test_commands:
        response = connection.query(cmd)
        if response.is_null():
            log_data[cmd.name] = None
        else:
            val = response.value
            if hasattr(val, "to_tuple"):
                val = val.to_tuple()
            else:
                val = str(val)
            log_data[cmd.name] = val

    logger.info({"event": "static_obd_snapshot", "data": log_data})

    # Close static connection
    connection.close()

    ############################################################################
    # 2) ASYNC TEST for 30 seconds
    ############################################################################
    # We watch the commands you suspect might return null in async:
    # COOLANT_TEMP, MAF, SPEED, THROTTLE_POS, etc.
    async_cmds = [
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.RPM,
        commands.SPEED,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS
    ]

    # Create an async connection
    async_connection = obd.Async(portstr="/dev/ttyUSB0")

    if not async_connection.is_connected():
        logger.error({"event": "connection_failure", "message": "Could not connect (async)"})
        return

    logger.info({"event": "connection_success", "message": "OBD-II connected (async)"})

    # Watch the commands, attach the callback
    with async_connection.paused() as was_running:
        for cmd in async_cmds:
            async_connection.watch(cmd, callback=async_callback, force=True)

    # Start async polling
    async_connection.start()

    # Let it run for 30 seconds
    start_time = time.time()
    MAX_RUNTIME = 30

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= MAX_RUNTIME:
                logger.info({"event": "async_test_ended", "elapsed_seconds": elapsed})
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info({"event": "shutdown_requested"})
    finally:
        # Stop the async connection
        async_connection.stop()
        logger.info({"event": "connection_stopped"})

    logger.info({"event": "finished_obd_test"})


if __name__ == "__main__":
    main()