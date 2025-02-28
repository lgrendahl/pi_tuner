#!/usr/bin/env python3

import time
import logging
from pythonjsonlogger import jsonlogger
import obd
from obd import commands

#
# ASYNC COMMANDS:   ENGINE_LOAD, COOLANT_TEMP, RPM, SPEED, INTAKE_TEMP, MAF, THROTTLE_POS
# SYNC COMMANDS:    (Everything else you care to query periodically)
#

# Create a global logger instance
logger = logging.getLogger("obd_logger")
logger.setLevel(logging.INFO)

# Set up JSON file logging with 2-space indent for readability
file_handler = logging.FileHandler("app.log")
formatter = jsonlogger.JsonFormatter(json_indent=2)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

##############################################################################
# 1. ASYNC CALLBACK
##############################################################################
def async_callback(response):
    """
    A callback function for new async data.
    'response' is an OBDResponse object containing .command and .value
    """
    if response.is_null():
        # No data returned
        logger.warning({
            "event": "async_snapshot",
            "command": response.command.name,
            "value": None
        })
        return

    # If there's a valid value, we check if it's numeric or not
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
    ############################################################################
    # 2. CREATE ASYNC CONNECTION
    ############################################################################
    # We use obd.Async() so that we can watch certain commands in near-real time.
    connection = obd.Async(portstr="/dev/ttyUSB0")  # adjust if needed

    # The commands you want to run asynchronously (fast polling in background)
    async_commands = [
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.RPM,
        commands.SPEED,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS
    ]

    # Pause the update loop before watch/unwatch calls
    with connection.paused() as was_running:
        # Subscribe each command to the async loop with our callback
        for cmd in async_commands:
            connection.watch(cmd, callback=async_callback, force=True)
            # 'force=True' if you want to poll it even if ECU might not list it as supported
            # Remove 'force=True' if you only want truly supported PIDs

    # Start the background loop (default interval).
    # You can provide a custom interval, e.g., connection.start(0.2) for 5Hz polling
    connection.start()

    ############################################################################
    # 3. SYNC POLLING FOR OTHER COMMANDS
    ############################################################################
    # These are commands you'd like to poll in a loop at a slower rate
    # Possibly once every 1 second, etc.
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

    try:
        while True:
            # For each sync command, query once
            snapshot = {}
            for cmd in sync_commands:
                response = connection.query(cmd)  # same as OBD.query(), blocking
                if not response.is_null():
                    val = response.value
                    if hasattr(val, "to_tuple"):
                        val = val.to_tuple()
                    else:
                        val = str(val)
                    snapshot[cmd.name] = val
                else:
                    snapshot[cmd.name] = None

            # Log an event with all sync results
            logger.info({
                "event": "sync_snapshot",
                "data": snapshot
            })

            # Sleep to define how often you poll sync commands
            time.sleep(1.0)

    except KeyboardInterrupt:
        logger.info({"event": "shutdown_requested"})
    finally:
        # Stop the async connection on exit
        connection.stop()

        logger.info({"event": "connection_stopped"})


if __name__ == "__main__":
    main()