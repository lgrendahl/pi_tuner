#!/usr/bin/env python3

import time
import logging
from pythonjsonlogger import jsonlogger
import obd
from obd import commands

###############################################################################
# CUSTOM JSON FORMATTER
###############################################################################
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    A custom JsonFormatter that removes empty `message`, flattens Python logging fields,
    and renames the timestamp key to `timestamp`.
    """

    def add_fields(self, log_record, record, message_dict):
        # Let the base class populate the default fields
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

        # Remove empty "message" if present
        if "message" in log_record and not log_record["message"]:
            del log_record["message"]

        # Rename "asctime" to "timestamp"
        if "asctime" in log_record:
            log_record["timestamp"] = log_record.pop("asctime")

        # You can remove other unwanted fields here, for example:
        for field in ["exc_info", "exc_text", "stack_info", "args"]:
            if field in log_record:
                del log_record[field]

###############################################################################
# CONFIGURE LOGGER (Single-Line JSON)
###############################################################################
logger = logging.getLogger("obd_logger")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("app.log")
formatter = CustomJsonFormatter()
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

###############################################################################
# HELPER: PARSE OBD VALUE
###############################################################################
def parse_obd_value(value_obj):
    """
    Returns a tuple (numeric_value, unit_string) if possible,
    otherwise returns (str(value_obj), None).
    Example:
        If value_obj.to_tuple() -> (10.588235294117647, [["percent", 1]]),
        we return (10.588235294117647, "percent").
    """
    if not value_obj or value_obj.is_null():
        return (None, None)

    # Try to parse numeric + units from the OBD response
    if hasattr(value_obj, "to_tuple"):
        val_tuple = value_obj.to_tuple()  # e.g. (10.58, [["percent", 1]])
        numeric_value = val_tuple[0]
        unit_str = None
        # Some OBD values store units in a structure like [["percent", 1]]
        if len(val_tuple) > 1 and val_tuple[1]:
            # val_tuple[1] might be something like [["percent", 1]]
            # so get the first item if it exists
            if len(val_tuple[1]) > 0 and len(val_tuple[1][0]) > 0:
                unit_str = val_tuple[1][0][0]
        return (numeric_value, unit_str)
    else:
        # Fallback: just convert to string
        return (str(value_obj), None)

###############################################################################
# ASYNC CALLBACK
###############################################################################
def async_callback(response):
    """
    Logs each new async reading in flattened JSON form.
    If response is null, logs None.
    """
    cmd = response.command.name if response.command else "UnknownCommand"
    if response.is_null():
        logger.info({"event": "async_snapshot", "command": cmd, "value": None})
        return

    numeric_value, unit_str = parse_obd_value(response.value)
    # Log a flattened JSON record
    rec = {
        "event": "async_snapshot",
        "command": cmd,
        "value": numeric_value
    }
    if unit_str:
        rec["unit"] = unit_str
    logger.info(rec)

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

    # Flatten all static data into a single record
    static_record = {"event": "static_obd_snapshot"}
    for cmd in static_commands:
        cmd_name = cmd.name
        if cmd in connection.supported_commands:
            resp = connection.query(cmd)
            val, unit_str = parse_obd_value(resp.value)
            static_record[cmd_name] = val
            if unit_str:
                static_record[cmd_name + "_unit"] = unit_str
        else:
            static_record[cmd_name] = None

    logger.info(static_record)

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

    max_runtime = 60
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