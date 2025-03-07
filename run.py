# Add to imports if not already present
from obd import commands

# In the main() function, modify the static_commands list:
static_commands = [
    commands.GET_DTC,  # Add this line first as it's a diagnostic command
    commands.ENGINE_LOAD,
    commands.COOLANT_TEMP,
    commands.RPM,
    commands.SPEED,
    commands.INTAKE_TEMP,
    commands.MAF,
    commands.THROTTLE_POS
]

# In the static queries section, modify the handling to accommodate DTCs:
# Replace or modify the static query loop with:
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

# Modify the InfluxDB writing section to handle DTCs:
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