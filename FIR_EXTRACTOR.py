import requests
import xml.etree.ElementTree as ET
import os

# URL to the XML data
url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Awaypoint_aisweb"

# Fetching the data from the URL
response = requests.get(url)
if response.status_code == 200:
    xml_data = response.content
else:
    print(f"Failed to retrieve data: {response.status_code}")
    exit()

# Parse the XML data
root = ET.fromstring(xml_data)

# Define the namespace dictionary
namespaces = {
    'ICA': 'http://10.32.62.212/geoserver/ICA',
    'gml': 'http://www.opengis.net/gml',
}

# Helper function to convert decimal degrees to DMS
def decimal_to_dms(coordinate, is_latitude=True):
    degrees = int(abs(coordinate))
    minutes = int((abs(coordinate) - degrees) * 60)
    seconds = (abs(coordinate) - degrees - minutes / 60) * 3600
    direction = 'N' if coordinate >= 0 else 'S' if is_latitude else 'E' if coordinate >= 0 else 'W'
    return f"{direction}{degrees:03d}.{minutes:02d}.{seconds:06.3f}"

# Extracting the ident, latitude, and longitude values
waypoints = []
for waypoint in root.findall('.//ICA:waypoint_aisweb', namespaces):
    ident = waypoint.find('ICA:ident', namespaces).text
    latitude = float(waypoint.find('ICA:latitude', namespaces).text)
    longitude = float(waypoint.find('ICA:longitude', namespaces).text)
    
    # Convert latitude and longitude to DMS format
    latitude_dms = decimal_to_dms(latitude, is_latitude=True)
    longitude_dms = decimal_to_dms(longitude, is_latitude=False)
    
    # Combine ident, latitude, and longitude into the required format
    waypoints.append(f"{ident};{latitude_dms};{longitude_dms};")

# Sort waypoints alphabetically by ident
waypoints_sorted = sorted(waypoints)

# Define the desktop path and the output file path
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
output_file = os.path.join(desktop_path, "fix.txt")

# Write the sorted and formatted waypoints to fix.txt
with open(output_file, 'w') as file:
    for waypoint in waypoints_sorted:
        file.write(f"{waypoint}\n")

print(f"Data has been saved to {output_file}")
