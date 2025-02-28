#!/usr/bin/env python3

import time
import logging
from pythonjsonlogger import jsonlogger
import obd
from obd import commands

###############################################################################
# CONFIGURE LOGGER (Single-Line JSON)
###############################################################################
logger = logging.getLogger("obd_logger")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("app.log")
# No 'json_indent' => single-line JSON
formatter = jsonlogger.JsonFormatter()
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

###############################################################################
# ASYNC CALLBACK
###############################################################################
def async_callback(response):
    """
    Logs each new async reading. If the response is null, logs None.
    """
    cmd = response.command.name if response.command else "UnknownCommand"
    if response.is_null():
        logger.info({"event": "async_snapshot", "command": cmd, "value": None})
        return

    val = response.value
    # If numeric, val may support .to_tuple()
    if hasattr(val, "to_tuple"):
        val = val.to_tuple()
    else:
        val = str(val)

    logger.info({"event": "async_snapshot", "command": cmd, "value": val})

###############################################################################
# MAIN SCRIPT
###############################################################################
def main():
    logger.info({"event": "starting_obd_test"})

    ############################################################################
    # 1) STATIC (SYNCHRONOUS) QUERIES
    ############################################################################
    # Confirmed Working Commands (from prior tests)
    static_commands = [
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.RPM,
        commands.SPEED,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS,
        commands.FUEL_STATUS,
        commands.SHORT_FUEL_TRIM_1,
        commands.LONG_FUEL_TRIM_1,
        commands.TIMING_ADVANCE,
        commands.O2_SENSORS,
        commands.O2_B1S1,
        commands.O2_B1S2,
        commands.OBD_COMPLIANCE
    ]

    connection = obd.OBD(portstr="/dev/ttyUSB0")
    if connection.is_connected():
        logger.info({"event": "connection_success", "message": "OBD-II connected (static)"})
    else:
        logger.error({"event": "connection_failure", "message": "Could not connect (static)"})
        return

    static_data = {}
    for cmd in static_commands:
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

    logger.info({"event": "static_obd_snapshot", "data": static_data})

    connection.close()  # close the static connection

    ############################################################################
    # 2) ASYNC TEST for 30 SECONDS
    ############################################################################
    # Only the commands you want real-time
    async_cmds = [
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.RPM,
        commands.SPEED,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS
    ]

    async_connection = obd.Async(portstr="/dev/ttyUSB0")
    if not async_connection.is_connected():
        logger.error({"event": "connection_failure", "message": "Could not connect (async)"})
        return

    logger.info({"event": "connection_success", "message": "OBD-II connected (async)"})

    # Must pause the loop before watch() calls
    with async_connection.paused():
        for cmd in async_cmds:
            # force=True if you want to query even if the ECU doesn't list them
            async_connection.watch(cmd, callback=async_callback, force=True)

    # Start the async loop, default interval
    async_connection.start()

    MAX_RUNTIME = 30  # seconds
    start_time = time.time()

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
        async_connection.stop()
        logger.info({"event": "async_connection_stopped"})

    logger.info({"event": "finished_obd_test"})

if __name__ == "__main__":
    main()