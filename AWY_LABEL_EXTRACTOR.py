import requests
import xml.etree.ElementTree as ET
import math
import logging

def convert_to_dms(decimal_degree):
    """Converts a decimal degree to degrees, minutes, seconds."""
    degrees = int(decimal_degree)
    minutes = int((abs(decimal_degree) - abs(degrees)) * 60)
    seconds = (abs(decimal_degree) - abs(degrees) - minutes / 60) * 3600
    return degrees, minutes, seconds

def format_label(txtdesig, lat, lon):
    """Formats the label in the desired format."""
    lat_deg, lat_min, lat_sec = convert_to_dms(lat)
    lon_deg, lon_min, lon_sec = convert_to_dms(lon)
    return f"L;{txtdesig};{'S' if lat < 0 else 'N'}{abs(lat_deg):03d}.{lat_min:02d}.{lat_sec:.3f};{'W' if lon < 0 else 'E'}{abs(lon_deg):03d}.{lon_min:02d}.{lon_sec:.3f};"

def haversine_distance(coord1, coord2):
    """Calculates the great-circle distance between two points given in decimal degrees."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = 6371.0 * c  # Radius of Earth in kilometers
    distance_nm = distance_km * 0.539957  # Convert to nautical miles
    return distance_nm

def process_airways(airway_data, upper_output_file, other_output_file):
    """Processes the airways and generates labels for segments longer than 10 NM, ensuring labels are not too close together."""
    with open(upper_output_file, 'w') as upper_file, open(other_output_file, 'w') as other_file:
        last_label_position = None
        
        for txtdesig, airwayseg, routedist, coord_tuples in airway_data:
            if routedist >= 10.0:
                # Calculate the midpoint for placing the label
                start = coord_tuples[0]
                end = coord_tuples[-1]
                mid_lat = (start[0] + end[0]) / 2
                mid_lon = (start[1] + end[1]) / 2
                label_position = (mid_lat, mid_lon)
                
                # Check the distance to the last label position to avoid overlap
                if last_label_position is None or haversine_distance(last_label_position, label_position) >= 10.0:
                    label = format_label(txtdesig, mid_lat, mid_lon)
                    last_label_position = label_position
                    
                    if txtdesig.startswith('U'):
                        upper_file.write(label + '\n')
                    else:
                        other_file.write(label + '\n')

# Set up logging
logging.basicConfig(level=logging.INFO)

# URL to the WFS service
url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Aairway"

# Fetch the data from the WFS service
response = requests.get(url)
response.raise_for_status()  # Ensure we got a successful response

# Parse the XML response
root = ET.fromstring(response.content)

# Namespace dictionary to handle the ICA namespace
ns = {'ICA': 'http://10.32.62.212/geoserver/ICA', 'gml': 'http://www.opengis.net/gml'}

# Find all airway elements
airways = root.findall('.//ICA:airway', ns)

# Extract relevant information and sort airways
airway_data = []

for airway in airways:
    try:
        txtdesig = airway.find('ICA:txtdesig', ns).text
        airwayseg = float(airway.find('ICA:airwayseg_', ns).text)
        routedist = float(airway.find('ICA:routedis', ns).text)
        
        coordinates_element = airway.find('.//gml:coordinates', ns)
        if coordinates_element is None:
            logging.warning(f"Coordinates not found for airway {txtdesig}. Skipping this entry.")
            continue

        coordinates = coordinates_element.text.strip()
        coord_pairs = coordinates.split(' ')
        coord_tuples = [(float(coord.split(',')[1]), float(coord.split(',')[0])) for coord in coord_pairs]

        airway_data.append((txtdesig, airwayseg, routedist, coord_tuples))

    except AttributeError as e:
        logging.error(f"Error extracting airway details: {e}")
        continue
    except ValueError as e:
        logging.error(f"Error converting numerical value: {e}")
        continue

# Sort by txtdesig and airwayseg_
airway_data.sort(key=lambda x: (x[0], x[1]))

# Process the sorted airways and output to separate files
upper_output_file = "upper_awy_label.txt"
other_output_file = "lower_awy_label.txt"
process_airways(airway_data, upper_output_file, other_output_file)
