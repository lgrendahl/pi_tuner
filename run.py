#!/usr/bin/env python3

import time
import logging
from pythonjsonlogger.json import JsonFormatter
import obd
from obd import commands

###############################################################################
# CONFIGURE LOGGER (Single-Line JSON)
###############################################################################
logger = logging.getLogger("obd_logger")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("app.log")
formatter = JsonFormatter()  # from pythonjsonlogger.json
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

    static_data = {}
    # Use membership check: if cmd in connection.supported_commands
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

    connection.close()
    time.sleep(0.03125)  # Give adapter a moment to reset

    ############################################################################
    # 2) ASYNC TEST (RUNS FOR 60 SECONDS)
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

    # Create Async OBD connection with recommended parameters
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

    # Pause the update loop before watch() calls
    with async_connection.paused():
        for cmd in async_cmds:
            if cmd in async_connection.supported_commands:
                async_connection.watch(cmd, callback=async_callback)
            else:
                logger.info({"event": "unsupported_command", "command": cmd.name})

    # Start the async loop
    async_connection.start()

    max_runtime = 600
    start_time = time.time()

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= max_runtime:
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