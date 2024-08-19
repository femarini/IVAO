import requests
import xml.etree.ElementTree as ET
import os

# URLs of the XML data
airway_url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Aairway"
waypoint_url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Awaypoint"
navaids_url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Anavaids"

# Fetch the XML data
airway_response = requests.get(airway_url)
airway_response.raise_for_status()

waypoint_response = requests.get(waypoint_url)
waypoint_response.raise_for_status()

navaids_response = requests.get(navaids_url)
navaids_response.raise_for_status()

# Parse the XML data
airway_root = ET.fromstring(airway_response.content)
waypoint_root = ET.fromstring(waypoint_response.content)
navaids_root = ET.fromstring(navaids_response.content)

# Define the namespace to avoid prefix issues
namespaces = {
    'wfs': "http://www.opengis.net/wfs",
    'gml': "http://www.opengis.net/gml",
    'ICA': "http://10.32.62.212/geoserver/ICA"
}

# Step 1: Fetch and store waypoint and navaids data
fixes = {}

# Load waypoints
for feature in waypoint_root.findall('gml:featureMember', namespaces):
    waypoint = feature.find('ICA:waypoint', namespaces)
    if waypoint is not None:
        ident = waypoint.find('ICA:ident', namespaces).text
        geom = waypoint.find('ICA:geom/gml:MultiPoint/gml:pointMember/gml:Point/gml:coordinates', namespaces)
        if geom is not None:
            coords = tuple(map(float, geom.text.strip().split(',')))
            fixes[coords] = ident

# Load navaids
for feature in navaids_root.findall('gml:featureMember', namespaces):
    navaid = feature.find('ICA:navaids', namespaces)
    if navaid is not None:
        designator = navaid.find('ICA:designator', namespaces).text
        geom = navaid.find('ICA:geom/gml:MultiPoint/gml:pointMember/gml:Point/gml:coordinates', namespaces)
        if geom is not None:
            coords = tuple(map(float, geom.text.strip().split(',')))
            fixes[coords] = designator

# Step 2: Extract airway segments categorized by txtdesig and seq
airways = {}

for feature in airway_root.findall('gml:featureMember', namespaces):
    airway = feature.find('ICA:airway', namespaces)
    if airway is not None:
        txtdesig_element = airway.find('ICA:txtdesig', namespaces)
        seq_element = airway.find('ICA:seq', namespaces)
        
        if txtdesig_element is not None and seq_element is not None:
            txtdesig = txtdesig_element.text
            seq = float(seq_element.text)
            
            geom_element = airway.find('ICA:geom/gml:LineString/gml:coordinates', namespaces)
            if geom_element is not None:
                segments = [tuple(map(float, segment.split(','))) for segment in geom_element.text.strip().split(' ')]
                
                if txtdesig not in airways:
                    airways[txtdesig] = []
                
                airways[txtdesig].append({
                    'seq': seq,
                    'segments': segments
                })
            else:
                print(f"Warning: 'coordinates' element not found for airway ID {airway.attrib.get('fid')}")

# Sort the segments by sequence and prepare the output
upper_airways_output = []
lower_airways_output = []

for txtdesig, segments in airways.items():
    segments.sort(key=lambda x: x['seq'])  # Sort by sequence
    
    for segment in segments:
        for lon, lat in segment['segments']:
            # Replace coordinates with waypoint or navaid ident/designator if it exists
            fix_ident = fixes.get((lon, lat), None)
            if fix_ident:
                track_line = f"T;{txtdesig};{fix_ident};{fix_ident};"
                if txtdesig.startswith('U'):
                    upper_airways_output.append(track_line)
                else:
                    lower_airways_output.append(track_line)

# Remove duplicates
upper_airways_output = list(dict.fromkeys(upper_airways_output))
lower_airways_output = list(dict.fromkeys(lower_airways_output))

# Determine the path to the desktop
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "awy.txt")

# Write the output to a file
with open(desktop_path, 'w') as file:
    # Write upper airways first
    for line in upper_airways_output:
        file.write(line + "\n")
    # Write lower airways after upper airways
    for line in lower_airways_output:
        file.write(line + "\n")

print(f"Output has been saved to {desktop_path}")
