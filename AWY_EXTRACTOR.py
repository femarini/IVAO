import requests
import xml.etree.ElementTree as ET
import os
import logging
from dataclasses import dataclass
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URLs of the XML data
airway_url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Aairway"
waypoint_url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Awaypoint"
navaids_url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Anavaids"

# Function to fetch and parse XML data
def fetch_and_parse_xml(url: str) -> Optional[ET.Element]:
    """
    Fetch XML data from the given URL and parse it.

    Args:
        url (str): URL to fetch the XML data from.

    Returns:
        ElementTree.Element: Parsed XML root element or None if an error occurred.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return ET.fromstring(response.content)
    except (requests.exceptions.RequestException, ET.ParseError) as e:
        logger.error(f"Error fetching or parsing data from {url}: {e}")
        return None

# Fetch the XML data
airway_root = fetch_and_parse_xml(airway_url)
waypoint_root = fetch_and_parse_xml(waypoint_url)
navaids_root = fetch_and_parse_xml(navaids_url)

# Check if data was successfully fetched
if airway_root is None or waypoint_root is None or navaids_root is None:
    logger.error("Failed to fetch and parse all required XML data. Exiting.")
    exit(1)

# Define namespaces manually
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
            coords = tuple(map(lambda x: round(float(x), 6), geom.text.strip().split(',')))
            fixes[coords] = ident

# Load navaids
for feature in navaids_root.findall('gml:featureMember', namespaces):
    navaid = feature.find('ICA:navaids', namespaces)
    if navaid is not None:
        designator = navaid.find('ICA:designator', namespaces).text
        geom = navaid.find('ICA:geom/gml:MultiPoint/gml:pointMember/gml:Point/gml:coordinates', namespaces)
        if geom is not None:
            coords = tuple(map(lambda x: round(float(x), 6), geom.text.strip().split(',')))
            fixes[coords] = designator

# Define a data class for airway segments
@dataclass
class AirwaySegment:
    seq: float
    segments: list

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
                segments = [tuple(map(lambda x: round(float(x), 6), segment.split(','))) for segment in geom_element.text.strip().split(' ')]
                
                if txtdesig not in airways:
                    airways[txtdesig] = []
                
                airways[txtdesig].append(AirwaySegment(seq=seq, segments=segments))
            else:
                logger.warning(f"'coordinates' element not found for airway ID {airway.attrib.get('fid')}")

# Sort the segments by sequence and prepare the output
upper_airways_output = []
lower_airways_output = []

for txtdesig, segments in airways.items():
    segments.sort(key=lambda x: x.seq)  # Sort by sequence
    
    for segment in segments:
        for lon, lat in segment.segments:
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

# Set output path to always save on Desktop
output_path = os.path.join(os.path.expanduser("~"), "Desktop", "awy.txt")

# Write the output to a file
with open(output_path, 'w') as file:
    # Write upper airways first
    for line in upper_airways_output:
        file.write(line + "\n")
    # Write lower airways after upper airways
    for line in lower_airways_output:
        file.write(line + "\n")

logger.info(f"Output has been saved to {output_path}")
