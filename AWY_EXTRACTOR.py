import requests
import xml.etree.ElementTree as ET
import os
import math

# URL of the XML data
url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Aairway"

# Fetch the XML data
response = requests.get(url)
response.raise_for_status()  # Raise an error if the request fails

# Parse the XML data
root = ET.fromstring(response.content)

# Define the namespace to avoid prefix issues
namespaces = {
    'wfs': "http://www.opengis.net/wfs",
    'gml': "http://www.opengis.net/gml",
    'ICA': "http://10.32.62.212/geoserver/ICA"
}

# Function to convert decimal degrees to DMS
def decimal_to_dms(deg, is_latitude):
    direction = 'N' if is_latitude and deg >= 0 else 'S' if is_latitude else 'E' if deg >= 0 else 'W'
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    s = (deg - d - m / 60) * 3600
    return f"{direction}{d:03d}.{m:02d}.{s:06.3f}"

# Function to check if three points are collinear (i.e., lie on the same straight line)
def is_collinear(p1, p2, p3):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    return abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)) < 1e-9

# Function to optimize the list of coordinates by keeping only necessary points
def optimize_track(coords):
    if len(coords) < 3:
        return coords
    optimized = [coords[0]]  # Start with the first point
    for i in range(1, len(coords) - 1):
        if not is_collinear(optimized[-1], coords[i], coords[i + 1]):
            optimized.append(coords[i])
    optimized.append(coords[-1])  # End with the last point
    return optimized

# Function to calculate the distance between two points (in NM)
def haversine(lon1, lat1, lon2, lat2):
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # Haversine formula
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    # Radius of earth in NM
    nm = 3440.065
    return nm * c

# Minimum distance between labels in NM
MIN_DISTANCE_NM = 50  # Change this to 20, 50, or 100 NM as needed

# Extract airway segments categorized by txtdesig and seq
airways = {}

for feature in root.findall('gml:featureMember', namespaces):
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
                optimized_segments = optimize_track(segments)
                
                if txtdesig not in airways:
                    airways[txtdesig] = []
                
                airways[txtdesig].append({
                    'seq': seq,
                    'segments': optimized_segments
                })
            else:
                print(f"Warning: 'coordinates' element not found for airway ID {airway.attrib.get('fid')}")

# Sort the segments by sequence and prepare the output
upper_airways_output = []
lower_airways_output = []

for txtdesig, segments in airways.items():
    segments.sort(key=lambda x: x['seq'])  # Sort by sequence
    
    last_label_position = None

    for segment in segments:
        for lon, lat in segment['segments']:
            dms_lat = decimal_to_dms(lat, is_latitude=True)
            dms_lon = decimal_to_dms(lon, is_latitude=False)
            track_line = f"T;{txtdesig};{dms_lat};{dms_lon};"
            label_line = f"L;{txtdesig};{dms_lat};{dms_lon};"
            
            if txtdesig.startswith('U'):
                upper_airways_output.append(track_line)
                if last_label_position is None or haversine(last_label_position[0], last_label_position[1], lon, lat) >= MIN_DISTANCE_NM:
                    upper_airways_output.append(label_line)
                    last_label_position = (lon, lat)
            else:
                lower_airways_output.append(track_line)
                if last_label_position is None or haversine(last_label_position[0], last_label_position[1], lon, lat) >= MIN_DISTANCE_NM:
                    lower_airways_output.append(label_line)
                    last_label_position = (lon, lat)

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
