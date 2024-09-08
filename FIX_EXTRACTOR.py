import xml.etree.ElementTree as ET
from collections import defaultdict
import requests
import sys
import re
import os

def fetch_xml(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def clean_xml(xml_string):
    # Replace problematic characters
    xml_string = xml_string.replace('Â°', '°')
    xml_string = xml_string.replace('Ã§', 'ç')
    xml_string = xml_string.replace('Ã£', 'ã')
    
    # Remove any other non-ASCII characters
    xml_string = re.sub(r'[^\x00-\x7F]+', '', xml_string)
    
    return xml_string

def parse_xml_safely(xml_string, parser_func, *args):
    try:
        cleaned_xml = clean_xml(xml_string)
        return parser_func(cleaned_xml, *args)
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        print("First 1000 characters of the cleaned XML:")
        print(cleaned_xml[:1000])
        print("\nLast 1000 characters of the cleaned XML:")
        print(cleaned_xml[-1000:])
        raise

def safe_get_text(element):
    return element.text if element is not None else None

def parse_waypoints(waypoint_xml):
    waypoints = {}
    root = ET.fromstring(waypoint_xml)
    ns = {'ICA': 'http://10.32.62.212/geoserver/ICA', 'gml': 'http://www.opengis.net/gml'}
    
    for waypoint in root.findall('.//ICA:waypoint_aisweb', ns):
        ident = safe_get_text(waypoint.find('ICA:ident', ns))
        coordinates = waypoint.find('.//gml:coordinates', ns)
        
        if ident and coordinates is not None and coordinates.text:
            coord_parts = coordinates.text.split(',')
            if len(coord_parts) == 2:
                lon, lat = map(float, coord_parts)
                waypoints[ident] = {
                    'coordinates': (lat, lon),  # Note: We swap lat and lon here
                    'used_in_airways': set()
                }
    
    return waypoints

def parse_airways(airway_xml, waypoints):
    airways = defaultdict(list)
    root = ET.fromstring(airway_xml)
    ns = {'ICA': 'http://10.32.62.212/geoserver/ICA', 'gml': 'http://www.opengis.net/gml'}
    
    for airway in root.findall('.//ICA:airway', ns):
        airway_name = safe_get_text(airway.find('ICA:name', ns))
        coordinates = airway.find('.//gml:coordinates', ns)
        
        if airway_name and coordinates is not None and coordinates.text:
            coord_pairs = [tuple(map(float, pair.split(','))) for pair in coordinates.text.split()]
            
            for lon, lat in coord_pairs:
                for ident, waypoint in waypoints.items():
                    if waypoint['coordinates'] == (lat, lon):
                        airways[airway_name].append(ident)
                        waypoint['used_in_airways'].add(airway_name)
                        break
    
    return airways

def main():
    waypoint_url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Awaypoint_aisweb"
    airway_url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Aairway"
    
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    output_file = os.path.join(desktop_path, "fixes.txt")
    
    try:
        print("Fetching waypoint data...")
        waypoint_xml = fetch_xml(waypoint_url)
        print("Fetching airway data...")
        airway_xml = fetch_xml(airway_url)
        
        print("Parsing waypoint data...")
        waypoints = parse_xml_safely(waypoint_xml, parse_waypoints)
        print(f"Parsed {len(waypoints)} waypoints.")
        
        print("Parsing airway data...")
        airways = parse_xml_safely(airway_xml, parse_airways, waypoints)
        print(f"Parsed {len(airways)} airways.")
        
        # Categorize fixes
        fixes_in_airways = set()
        for airway, fixes in airways.items():
            fixes_in_airways.update(fixes)
        
        fixes_not_in_airways = set(waypoints.keys()) - fixes_in_airways
        
        with open(output_file, 'w') as f:
            # Output fixes used in airways
            for fix in sorted(fixes_in_airways):
                lat, lon = waypoints[fix]['coordinates']
                f.write(f"{fix};{lat};{lon};0;0\n")
            
            # Output fixes not used in airways
            for fix in sorted(fixes_not_in_airways):
                lat, lon = waypoints[fix]['coordinates']
                f.write(f"{fix};{lat};{lon};1;0\n")
        
        print(f"Output has been written to {output_file}")
        print(f"Total fixes: {len(waypoints)}")
        print(f"Fixes used in airways: {len(fixes_in_airways)}")
        print(f"Fixes not used in airways: {len(fixes_not_in_airways)}")
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching data: {e}")
    except ET.ParseError as e:
        print(f"An error occurred while parsing XML: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Python version:", sys.version)
        print("ElementTree version:", ET.VERSION)
        print("Requests version:", requests.__version__)

if __name__ == "__main__":
    main()
