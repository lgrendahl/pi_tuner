#!/usr/bin/env python3

import logging
from pythonjsonlogger import jsonlogger
import obd
from obd import OBDCommand, commands

def main():
    # ---------------------------------------------------------
    # 1. Configure JSON Logger
    # ---------------------------------------------------------
    logger = logging.getLogger("obd_logger")
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler("pid_check.log")
    formatter = jsonlogger.JsonFormatter()
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info({"event": "starting_pid_check"})

    # ---------------------------------------------------------
    # 2. Connect to OBD-II
    # ---------------------------------------------------------
    connection = obd.OBD(portstr="/dev/ttyUSB0")
    if connection.is_connected():
        logger.info({"event": "connection_success", "message": "OBD-II connected"})
    else:
        logger.error({"event": "connection_failure", "message": "Could not connect to OBD-II"})
        return

    # ---------------------------------------------------------
    # 3. Full List of Mode 01 PIDs from Official Docs
    #    (As they appear in python-OBD)
    # ---------------------------------------------------------
    # Not all of these might be in python-OBD commands.*,
    # but we'll list them as an example. Remove or comment out
    # any that cause AttributeErrors if not implemented.
    mode_01_commands = [
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
        # Some additional ones if python-OBD supports them:
        commands.FUEL_LEVEL,
        commands.ETHANOL_PERCENT,
        commands.EVAP_VAPOR_PRESSURE_ABS,
        commands.EVAP_VAPOR_PRESSURE_ALT,
        commands.OIL_TEMP,
        commands.FUEL_INJECT_TIMING,
        # etc. (Add any others from the doc that python-OBD provides)
    ]

    # ---------------------------------------------------------
    # 4. Check & Query Each Command
    # ---------------------------------------------------------
    results = {}
    for cmd in mode_01_commands:
        # Check if the ECU reports this PID as supported
        if connection.supports(cmd):
            response = connection.query(cmd)
            if not response.is_null():
                # Attempt to handle numeric vs. bit arrays vs. string
                val = response.value
                # Some responses (like numeric) have .to_tuple()
                if hasattr(val, "to_tuple"):
                    val = val.to_tuple()
                else:
                    # Fallback: store string representation for bit arrays / special
                    val = str(val)

                results[cmd.name] = {
                    "supported": True,
                    "raw_value": val
                }
            else:
                # The ECU claims it's supported, but no data returned
                results[cmd.name] = {
                    "supported": True,
                    "raw_value": None
                }
        else:
            # Not supported by this vehicle
            results[cmd.name] = {
                "supported": False
            }
            # Optionally log a warning
            logger.warning({
                "event": "unsupported_cmd",
                "cmd": cmd.name
            })

    # ---------------------------------------------------------
    # 5. Write a Summary to the Log
    # ---------------------------------------------------------
    # You can log in bulk, or just log each command in the loop above.
    logger.info({
        "event": "pid_check_summary",
        "results": results
    })

    logger.info({"event": "finished_pid_check"})


if __name__ == "__main__":
    main()