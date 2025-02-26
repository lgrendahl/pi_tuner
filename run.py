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
                     obd.commands.COOLANT_TEMP,
                     obd.commands.PIDS_A,
                     obd.commands.STATUS,
                     obd.commands.FREEZE_DTC,
                     obd.commands.FUEL_STATUS,
                     obd.commands.ENGINE_LOAD,
                     obd.commands.COOLANT_TEMP,
                     obd.commands.SHORT_FUEL_TRIM_1,
                     obd.commands.LONG_FUEL_TRIM_1,
                     obd.commands.SHORT_FUEL_TRIM_2,
                     obd.commands.LONG_FUEL_TRIM_2,
                     obd.commands.FUEL_PRESSURE,
                     obd.commands.INTAKE_PRESSURE,
                     obd.commands.RPM,
                     obd.commands.SPEED,
                     obd.commands.TIMING_ADVANCE,
                     obd.commands.INTAKE_TEMP,
                     obd.commands.MAF,
                     obd.commands.THROTTLE_POS,
                     obd.commands.AIR_STATUS,
                     obd.commands.O2_SENSORS,
                     obd.commands.O2_B1S1,
                     obd.commands.O2_B1S2,
                     obd.commands.O2_B1S3,
                     obd.commands.O2_B1S4,
                     obd.commands.O2_B2S1,
                     obd.commands.O2_B2S2,
                     obd.commands.O2_B2S3,
                     obd.commands.O2_B2S4,
                     obd.commands.OBD_COMPLIANCE,
                     obd.commands.O2_SENSORS_ALT,
                     obd.commands.AUX_INPUT_STATUS,
                     obd.commands.RUN_TIME,
                     obd.commands.PIDS_B,
                     obd.commands.DISTANCE_W_MIL,
                     obd.commands.FUEL_RAIL_PRESSURE_VAC,
                     obd.commands.FUEL_RAIL_PRESSURE_DIRECT,
                     obd.commands.FUEL_LEVEL,
                     obd.commands.ETHANOL_PERCENT,
                     obd.commands.EVAP_VAPOR_PRESSURE_ABS,
                     obd.commands.EVAP_VAPOR_PRESSURE_ALT,
                     obd.commands.OIL_TEMP,
                     obd.commands.FUEL_INJECT_TIMING]

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