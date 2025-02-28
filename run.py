#!/usr/bin/env python3

import logging
from pythonjsonlogger import jsonlogger
import obd
from obd import commands

def main():
    # ---------------------------------------------------------
    # 1. Configure JSON Logger (with 2-space indentation)
    # ---------------------------------------------------------
    logger = logging.getLogger("obd_logger")
    logger.setLevel(logging.INFO)

    # Create a FileHandler
    file_handler = logging.FileHandler("app.log")

    # jsonlogger.JsonFormatter supports indentation via "json_indent"
    formatter = jsonlogger.JsonFormatter(json_indent=2)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info({"event": "starting_obd_test"})

    # ---------------------------------------------------------
    # 2. Connect to OBD-II
    # ---------------------------------------------------------
    connection = obd.OBD(portstr="/dev/ttyUSB0")  # Adjust if needed
    if connection.is_connected():
        logger.info({"event": "connection_success", "message": "OBD-II connected"})
    else:
        logger.error({"event": "connection_failure", "message": "Could not connect to OBD-II"})
        return

    # ---------------------------------------------------------
    # 3. Only Supported PIDs (from your previous pid_check)
    # ---------------------------------------------------------
    test_commands = [
        commands.PIDS_A,
        commands.STATUS,
        commands.FUEL_STATUS,
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.SHORT_FUEL_TRIM_1,
        commands.LONG_FUEL_TRIM_1,
        commands.RPM,
        commands.SPEED,
        commands.TIMING_ADVANCE,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS,
        commands.O2_SENSORS,
        commands.O2_B1S1,
        commands.O2_B1S2,
        commands.OBD_COMPLIANCE
    ]

    # ---------------------------------------------------------
    # 4. Query & Collect Data
    # ---------------------------------------------------------
    log_data = {}
    for cmd in test_commands:
        response = connection.query(cmd)
        if response.is_null():
            # ECU returned no data
            log_data[cmd.name] = None
        else:
            val = response.value
            # If the response object has .to_tuple(), it's usually numeric + units
            if hasattr(val, "to_tuple"):
                log_data[cmd.name] = val.to_tuple()
            else:
                # For bit arrays, strings, or other custom data
                log_data[cmd.name] = str(val)

    # ---------------------------------------------------------
    # 5. Log a Pretty-Printed Snapshot of All Data
    # ---------------------------------------------------------
    logger.info({
        "event": "obd_snapshot",
        "data": log_data
    })

    logger.info({"event": "finished_obd_test"})


if __name__ == "__main__":
    main()