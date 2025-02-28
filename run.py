#!/usr/bin/env python3

import logging
from pythonjsonlogger import jsonlogger
import obd
from obd import commands

def main():
    # ---------------------------------------------------------
    # 1. Configure JSON Logger
    # ---------------------------------------------------------
    logger = logging.getLogger("obd_logger")
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler("app.log")
    formatter = jsonlogger.JsonFormatter()
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
    # 3. Only Supported PIDs (from pid_check.log)
    # ---------------------------------------------------------
    # These PIDs returned valid data for your specific Miata. Feel free to
    # adjust or add others if you discover more are supported.
    test_commands = [
        commands.PIDS_A,          # returns a BitArray of supported PIDs [01-20]
        commands.STATUS,          # sometimes returns null or a special status
        commands.FUEL_STATUS,     # string or tuple (e.g. "Open loop")
        commands.ENGINE_LOAD,     # numeric
        commands.COOLANT_TEMP,    # numeric
        commands.SHORT_FUEL_TRIM_1,
        commands.LONG_FUEL_TRIM_1,
        commands.RPM,             # numeric
        commands.SPEED,           # numeric
        commands.TIMING_ADVANCE,  # numeric
        commands.INTAKE_TEMP,     # numeric
        commands.MAF,             # numeric
        commands.THROTTLE_POS,    # numeric
        commands.O2_SENSORS,      # typically a bit array or special structure
        commands.O2_B1S1,         # numeric (voltage)
        commands.O2_B1S2,         # numeric (voltage)
        commands.OBD_COMPLIANCE   # string (e.g. "OBD-II as defined by the CARB")
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
    # 5. Log a Snapshot of All Data
    # ---------------------------------------------------------
    logger.info({
        "event": "obd_snapshot",
        "data": log_data
    })

    logger.info({"event": "finished_obd_test"})


if __name__ == "__main__":
    main()