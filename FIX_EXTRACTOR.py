import pandas as pd
import re

# Configuration dictionary for types
extract_types = {
    "ICAO": True,
    "TERMINAL": True,
    "OTHER:ADHP": True,
    "BRG_DIST": True,
    "DESIGNED": True,
    "OTHER": True,
    "COORD": True,
}


# Function to convert DMS to formatted string with direction and fixed format
def dms_to_formatted_with_direction(dms_str):
    match = re.match(r'(\d+)°(\d+)\'(\d+\.\d+)" ([NSWE])', dms_str)
    if match:
        degrees, minutes, seconds, direction = match.groups()
        return f"{direction}{int(degrees):03}.{int(minutes):02}.{float(seconds):06.2f}"
    return None


# Function to get the code based on the type of waypoint
def get_code(tipo):
    return "1" if tipo in extract_types else "Unknown Code"


# Function to format waypoint data into a DataFrame
def format_waypoint_data(waypoints_df, section_name, exclude_waypoints=set()):
    waypoints_df = waypoints_df[waypoints_df["tipo"].isin(extract_types)]
    waypoints_df = waypoints_df[~waypoints_df["ident"].isin(exclude_waypoints)]
    formatted_lines = waypoints_df.apply(
        lambda row: f"{row['ident']};{dms_to_formatted_with_direction(row['latitude_gms'])};{dms_to_formatted_with_direction(row['longitude_gms'])};{get_code(row['tipo'])};",
        axis=1,
    )
    return f"//{section_name}\n" + "\n".join(formatted_lines) + "\n\n"


# Function to extract en route waypoints and format them
def extract_en_route_waypoints(waypoint_data, aerovia_data, section_name):
    en_route_waypoints = set(aerovia_data["from_fix_ident"]).union(
        aerovia_data["to_fix_ident"]
    )
    filtered_waypoint_data = waypoint_data[
        waypoint_data["ident"].isin(en_route_waypoints)
    ]
    formatted_lines = filtered_waypoint_data.apply(
        lambda row: f"{row['ident']};{dms_to_formatted_with_direction(row['latitude_gms'])};{dms_to_formatted_with_direction(row['longitude_gms'])};0;",
        axis=1,
    )
    return (
        f"//{section_name}\n" + "\n".join(formatted_lines) + "\n\n",
        en_route_waypoints,
    )


# Load data
waypoint_data = pd.read_excel("waypoint_aisweb.xls")
aerovia_data = pd.concat(
    [pd.read_excel("vw_aerovia_alta_v2.xls"), pd.read_excel("vw_aerovia_baixa_v2.xls")]
)

# Process data
awy_section, en_route_waypoints = extract_en_route_waypoints(
    waypoint_data, aerovia_data, "--AIRWAY FIXES--"
)
fixes_section = format_waypoint_data(
    waypoint_data, "-- TERMINAL FIXES--", en_route_waypoints
)

# Write to file
with open("fixes.txt", "w") as f:
    f.write(f"{fixes_section}{awy_section}")
