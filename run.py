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
    # 1) STATIC (SYNCHRONOUS) QUERIES (OPTIONAL)
    #    Demonstrates a single pass of known PIDs before we move to Async.
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

    connection = obd.OBD(
        portstr="/dev/ttyUSB0",
        fast=False,       # be conservative for reliability
        timeout=1.0       # in case the ECU is slow
    )
    if connection.is_connected():
        logger.info({"event": "connection_success", "message": "OBD-II connected (static)"})
    else:
        logger.error({"event": "connection_failure", "message": "Could not connect (static)"})
        return

    static_data = {}
    for cmd in static_commands:
        if connection.supports_command(cmd):
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
            static_data[cmd.name] = None  # or "unsupported"

    logger.info({"event": "static_obd_snapshot", "data": static_data})

    connection.close()  # close the static connection

    # Wait a moment so the ELM327 can reset/settle
    time.sleep(2)

    ############################################################################
    # 2) ASYNC TEST for 60 SECONDS
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

    # Build the Async connection with recommended parameters
    async_connection = obd.Async(
        portstr="/dev/ttyUSB0",
        fast=False,       # avoid "fast" mode for flaky ELM clones or slower ECUs
        timeout=1.0,      # give enough time for ECU to respond
        delay_cmds=0.5    # add a delay between command loops
    )

    if not async_connection.is_connected():
        logger.error({"event": "connection_failure", "message": "Could not connect (async)"})
        return

    logger.info({"event": "connection_success", "message": "OBD-II connected (async)"})

    # Must pause the loop before watch() calls
    with async_connection.paused():
        for cmd in async_cmds:
            # Only watch if the ECU actually supports the command:
            if async_connection.supports_command(cmd):
                async_connection.watch(cmd, callback=async_callback)
            else:
                logger.info({"event": "unsupported_command", "command": cmd.name})

    # Start the async loop
    async_connection.start()

    MAX_RUNTIME = 60  # seconds
    start_time = time.time()

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= MAX_RUNTIME:
                logger.info({"event": "async_test_ended", "elapsed_seconds": elapsed})
                break
            # Sleep briefly to avoid hammering the CPU
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info({"event": "shutdown_requested"})
    finally:
        async_connection.stop()
        logger.info({"event": "async_connection_stopped"})

    logger.info({"event": "finished_obd_test"})

if __name__ == "__main__":
    main()