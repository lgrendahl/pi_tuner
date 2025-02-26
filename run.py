#!/usr/bin/env python3

import obd
import logging
from pythonjsonlogger import jsonlogger

def main():
    # ---------------------------------------------------------
    # 1. Configure JSON Logger
    # ---------------------------------------------------------
    logger = logging.getLogger("obd_logger")
    logger.setLevel(logging.INFO)

    # Log to a file named app.log (adjust path if you prefer)
    file_handler = logging.FileHandler("app.log")
    formatter = jsonlogger.JsonFormatter()
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info({"event": "starting_obd_test"})

    # ---------------------------------------------------------
    # 2. Connect to OBD-II
    # ---------------------------------------------------------
    # Adjust 'portstr' to match the actual device name, e.g. /dev/ttyUSB0 or /dev/ttyACM0
    connection = obd.OBD(portstr="/dev/ttyUSB0")

    if connection.is_connected():
        logger.info({"event": "connection_success", "message": "OBD-II connected"})
    else:
        logger.error({"event": "connection_failure", "message": "Could not connect to OBD-II"})
        return

    # ---------------------------------------------------------
    # 3. Query Some Common PIDs
    # ---------------------------------------------------------
    # Typically, older cars might not support all PIDs. Test a few basics first.
    test_commands = [obd.commands.RPM,
                     obd.commands.SPEED,
                     obd.commands.COOLANT_TEMP]

    # Collect a single snapshot to keep it simple
    log_data = {}
    for cmd in test_commands:
        response = connection.query(cmd)
        # Convert command name and response value to JSON-friendly format
        log_data[cmd.name] = response.value.to_tuple() if not response.is_null() else None

    # Log the data in JSON format
    logger.info({
        "event": "obd_snapshot",
        "data": log_data
    })

    logger.info({"event": "finished_obd_test"})

if __name__ == "__main__":
    main()