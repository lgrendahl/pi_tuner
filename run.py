import obd
from obd import commands
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import time
import os
from datetime import datetime

# InfluxDB configuration
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "your-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "your-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "car-data")


def connect_obd():
    connection = obd.OBD()
    if not connection.is_connected():
        print("Failed to connect to OBD adapter")
        return None
    return connection


def main():
    # Connect to OBD
    connection = connect_obd()
    if not connection:
        return

    # Connect to InfluxDB
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Define the commands to query
    static_commands = [
        commands.GET_DTC,
        commands.ENGINE_LOAD,
        commands.COOLANT_TEMP,
        commands.RPM,
        commands.SPEED,
        commands.INTAKE_TEMP,
        commands.MAF,
        commands.THROTTLE_POS
    ]

    try:
        while True:
            # Query static commands
            static_data = {}
            for cmd in static_commands:
                if cmd in connection.supported_commands:
                    resp = connection.query(cmd)
                    if resp.is_null():
                        static_data[cmd.name] = None
                    else:
                        val = resp.value
                        if cmd == commands.GET_DTC:
                            # Special handling for DTCs
                            dtc_list = []
                            for dtc_code, dtc_desc in val:
                                dtc_info = {
                                    "code": dtc_code,
                                    "description": dtc_desc if dtc_desc else "Unknown DTC"
                                }
                                dtc_list.append(dtc_info)
                            static_data[cmd.name] = dtc_list
                        else:
                            # Existing handling for other commands
                            if hasattr(val, "to_tuple"):
                                val = val.to_tuple()
                            else:
                                val = str(val)
                            static_data[cmd.name] = val
                else:
                    static_data[cmd.name] = None

            # Prepare data for InfluxDB
            fields = {}
            for k, v in static_data.items():
                if v is None:
                    continue
                if k == "GET_DTC":
                    # Handle DTCs specially
                    if v:  # if there are any DTCs
                        fields["dtc_count"] = len(v)
                        for i, dtc in enumerate(v):
                            fields[f"dtc_{i}_code"] = dtc["code"]
                            fields[f"dtc_{i}_desc"] = dtc["description"]
                else:
                    # Existing handling for other values
                    if isinstance(v, tuple):
                        numeric_value = v[0]
                        unit = None
                        if len(v) > 1 and v[1]:
                            if len(v[1][0]) > 0:
                                unit = v[1][0][0]
                        fields[k] = numeric_value
                        if unit:
                            fields[k + "_unit"] = unit
                    else:
                        fields[k + "_str"] = v

            # Write to InfluxDB
            if fields:
                point = {
                    "measurement": "car_data",
                    "fields": fields,
                    "time": datetime.utcnow()
                }
                write_api.write(bucket=INFLUX_BUCKET, record=point)

            time.sleep(1)  # Wait 1 second before next query

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if 'client' in locals():
            client.close()
        if 'connection' in locals():
            connection.close()


if __name__ == "__main__":
    main()