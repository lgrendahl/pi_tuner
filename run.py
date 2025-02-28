#!/usr/bin/env python3

import time
import logging
from pythonjsonlogger import jsonlogger
import obd
from obd import commands

#
# ASYNC COMMANDS:   ENGINE_LOAD, COOLANT_TEMP, RPM, SPEED, INTAKE_TEMP, MAF, THROTTLE_POS
# SYNC COMMANDS:    FUEL_STATUS, SHORT_FUEL_TRIM_1, LONG_FUEL_TRIM_1, TIMING_ADVANCE, etc.
#

logger = logging.getLogger("obd_logger")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("app.log")
formatter = jsonlogger.JsonFormatter(json_indent=2)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# How long (in seconds) to run before stopping. Here, 10 minutes = 600 seconds.
MAX_RUNTIME = 600

def async_callback(response):
    """
    Fires each time a new async reading is received.
    """
    if response.is_null():
        logger.warning({
            "event": "async_snapshot",
            "command": response.command.name,
            "value": None
        })
        return

    val = response.value
    if hasattr(val, "to_tuple"):
        val = val.to_tuple()
    else:
        val = str(val)

    logger.info({
        "event": "async_snapshot",
        "command": response.command.name,
        "value": val
    })

def main():
    # 1) Initialize Async Connection
    connection = obd.Async(portstr="/dev/ttyUSB0")

    # These commands will be polled rapidly in the background (async)
    async_commands = [
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.RPM,
        commands.SPEED,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS
    ]

    # Pause the update loop to safely watch commands
    with connection.paused() as was_running:
        for cmd in async_commands:
            connection.watch(cmd, callback=async_callback, force=True)

    # Start the async loop
    connection.start()

    # 2) Synchronous commands we poll once every second
    sync_commands = [
        commands.FUEL_STATUS,
        commands.SHORT_FUEL_TRIM_1,
        commands.LONG_FUEL_TRIM_1,
        commands.TIMING_ADVANCE,
        commands.O2_SENSORS,
        commands.O2_B1S1,
        commands.O2_B1S2,
        commands.OBD_COMPLIANCE
    ]

    # Log the start event
    logger.info({"event": "test_started", "duration_seconds": MAX_RUNTIME})

    start_time = time.time()

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= MAX_RUNTIME:
                logger.info({
                    "event": "test_ended",
                    "duration_reached": elapsed
                })
                break

            # Poll each sync command once
            snapshot = {}
            for cmd in sync_commands:
                response = connection.query(cmd)
                if not response.is_null():
                    val = response.value
                    if hasattr(val, "to_tuple"):
                        val = val.to_tuple()
                    else:
                        val = str(val)
                    snapshot[cmd.name] = val
                else:
                    snapshot[cmd.name] = None

            logger.info({"event": "sync_snapshot", "data": snapshot})

            time.sleep(1.0)

    except KeyboardInterrupt:
        logger.info({"event": "shutdown_requested"})
    finally:
        # Ensure the async connection is stopped before exiting
        connection.stop()
        logger.info({"event": "connection_stopped"})


if __name__ == "__main__":
    main()