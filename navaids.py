import xml.etree.ElementTree as ET
from collections import defaultdict
import requests
import sys
import re
import os
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    BASE_URL = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows"
    WAYPOINT_TYPE = "ICA:waypoint_aisweb"
    AIRWAY_TYPE = "ICA:airway"
    VOR_TYPE = "ICA:vor"
    NDB_TYPE = "ICA:ndb"
    NAMESPACE = {
        'ICA': 'http://10.32.62.212/geoserver/ICA',
        'gml': 'http://www.opengis.net/gml'
    }
    OUTPUT_FILE = "navaids.txt"

def fetch_xml(url, timeout=30):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.Timeout:
        raise Exception(f"Request timed out after {timeout} seconds: {url}")
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch URL {url}: {str(e)}")

def clean_xml(xml_string):
    replacements = {
        'Â°': '°',
        'Ã§': 'ç',
        'Ã£': 'ã',
        'Ã©': 'é',
        'Ã¢': 'â',
    }
    for old, new in replacements.items():
        xml_string = xml_string.replace(old, new)
    xml_string = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', xml_string)
    return xml_string

def parse_xml_safely(xml_string, parser_func, *args):
    try:
        cleaned_xml = clean_xml(xml_string)
        return parser_func(cleaned_xml, *args)
    except ET.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        logger.debug("First 1000 characters of the cleaned XML:")
        logger.debug(cleaned_xml[:1000])
        logger.debug("\nLast 1000 characters of the cleaned XML:")
        logger.debug(cleaned_xml[-1000:])
        raise

def safe_get_text(element):
    return element.text.strip() if element is not None and element.text else None

def parse_coordinates(coord_string):
    try:
        if not coord_string:
            return None
        lon, lat = map(float, coord_string.split(','))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            logger.warning(f"Invalid coordinates: ({lat}, {lon})")
            return None
        return (lat, lon)
    except (ValueError, AttributeError):
        return None

def parse_waypoints(waypoint_xml):
    waypoints = {}
    root = ET.fromstring(waypoint_xml)
    
    for waypoint in root.findall('.//ICA:waypoint_aisweb', Config.NAMESPACE):
        ident = safe_get_text(waypoint.find('ICA:ident', Config.NAMESPACE))
        coords_elem = waypoint.find('.//gml:coordinates', Config.NAMESPACE)
        coords = parse_coordinates(safe_get_text(coords_elem))
        
        if ident and coords:
            waypoints[ident] = {
                'coordinates': coords,
                'used_in_airways': set()
            }
    return waypoints

def parse_airways(airway_xml, waypoints):
    airways = defaultdict(list)
    root = ET.fromstring(airway_xml)
    
    for airway in root.findall('.//ICA:airway', Config.NAMESPACE):
        airway_name = safe_get_text(airway.find('ICA:name', Config.NAMESPACE))
        coordinates = airway.find('.//gml:coordinates', Config.NAMESPACE)
        
        if airway_name and coordinates is not None and coordinates.text:
            coord_pairs = [parse_coordinates(pair) for pair in coordinates.text.split()]
            coord_pairs = [pair for pair in coord_pairs if pair is not None]
            
            for lat, lon in coord_pairs:
                for ident, waypoint in waypoints.items():
                    if waypoint['coordinates'] == (lat, lon):
                        airways[airway_name].append(ident)
                        waypoint['used_in_airways'].add(airway_name)
                        break
    return airways

def gms_to_decimal(gms_str):
    try:
        degrees, minutes_seconds = gms_str.split("°")
        minutes, seconds_hemisphere = minutes_seconds.split("'")
        seconds = seconds_hemisphere[:-2].replace('"', '')
        hemisphere = seconds_hemisphere[-1]
        
        formatted_str = f"{degrees.zfill(3)}.{minutes.zfill(2)}.{seconds.zfill(2)}.000"
        return f"{hemisphere}{formatted_str}"
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse GMS string '{gms_str}': {str(e)}")
        return None

def parse_vor(vor_xml):
    vors = []
    root = ET.fromstring(vor_xml)
    
    for vor in root.findall('.//ICA:vor', Config.NAMESPACE):
        ident = safe_get_text(vor.find('ICA:ident', Config.NAMESPACE))
        frequency = safe_get_text(vor.find('ICA:frequency', Config.NAMESPACE))
        lat_gms = safe_get_text(vor.find('ICA:latitude_gms', Config.NAMESPACE))
        lon_gms = safe_get_text(vor.find('ICA:longitude_gms', Config.NAMESPACE))
        
        if all([ident, frequency, lat_gms, lon_gms]):
            lat_formatted = gms_to_decimal(lat_gms)
            lon_formatted = gms_to_decimal(lon_gms)
            if lat_formatted and lon_formatted:
                vors.append({
                    'ident': ident,
                    'frequency': frequency,
                    'latitude': lat_formatted,
                    'longitude': lon_formatted
                })
    return vors

def parse_ndb(ndb_xml):
    ndbs = []
    root = ET.fromstring(ndb_xml)
    
    for ndb in root.findall('.//ICA:ndb', Config.NAMESPACE):
        ident = safe_get_text(ndb.find('ICA:codeid', Config.NAMESPACE))
        frequency = safe_get_text(ndb.find('ICA:valfreq', Config.NAMESPACE))
        lat_gms = safe_get_text(ndb.find('ICA:latitude_gms', Config.NAMESPACE))
        lon_gms = safe_get_text(ndb.find('ICA:longitude_gms', Config.NAMESPACE))
        
        if all([ident, frequency, lat_gms, lon_gms]):
            lat_formatted = gms_to_decimal(lat_gms)
            lon_formatted = gms_to_decimal(lon_gms)
            if lat_formatted and lon_formatted:
                ndbs.append({
                    'ident': ident,
                    'frequency': frequency,
                    'latitude': lat_formatted,
                    'longitude': lon_formatted
                })
    return ndbs

def format_coordinates(lat, lon):
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    lat = abs(lat)
    lon = abs(lon)
    
    lat_deg = int(lat)
    lat_min = int((lat - lat_deg) * 60)
    lat_sec = round(((lat - lat_deg) * 60 - lat_min) * 60, 3)
    
    lon_deg = int(lon)
    lon_min = int((lon - lon_deg) * 60)
    lon_sec = round(((lon - lon_deg) * 60 - lon_min) * 60, 3)
    
    return f"{lat_dir}{lat_deg:03d}.{lat_min:02d}.{lat_sec:06.3f}", f"{lon_dir}{lon_deg:03d}.{lon_min:02d}.{lon_sec:06.3f}"

def write_output(file, waypoints, fixes_in_airways, fixes_not_in_airways, vors, ndbs):
    # Write FIXES section
    file.write("[FIXES]\n")
    file.write("//" * 50 + "\n")
    for fix in sorted(fixes_in_airways):
        lat, lon = waypoints[fix]['coordinates']
        lat_str, lon_str = format_coordinates(lat, lon)
        file.write(f"{fix};{lat_str};{lon_str};0;0\n")
    for fix in sorted(fixes_not_in_airways):
        lat, lon = waypoints[fix]['coordinates']
        lat_str, lon_str = format_coordinates(lat, lon)
        file.write(f"{fix};{lat_str};{lon_str};1;0\n")
    
    # Write VOR section
    file.write("\n[VOR]\n")
    file.write("//" * 50 + "\n")
    for vor in vors:
        file.write(f"{vor['ident']};{vor['frequency']};{vor['latitude']};{vor['longitude']};\n")
    
    # Write NDB section
    file.write("\n[NDB]\n")
    file.write("//" * 50 + "\n")
    for ndb in ndbs:
        file.write(f"{ndb['ident']};{ndb['frequency']};{ndb['latitude']};{ndb['longitude']};\n")

def print_results(output_file, waypoints, fixes_in_airways, fixes_not_in_airways, vors, ndbs):
    logger.info(f"Output written to {output_file}")
    logger.info(f"Total fixes: {len(waypoints)}")
    logger.info(f"Fixes in airways: {len(fixes_in_airways)}")
    logger.info(f"Fixes not in airways: {len(fixes_not_in_airways)}")
    logger.info(f"VORs processed: {len(vors)}")
    logger.info(f"NDBs processed: {len(ndbs)}")

def parse_args():
    parser = argparse.ArgumentParser(description="Process waypoint, airway, VOR, and NDB data")
    parser.add_argument("--output-dir", default=os.path.expanduser("~/Desktop"), help="Output directory")
    return parser.parse_args()

def main():
    args = parse_args()
    urls = {
        'waypoints': f"{Config.BASE_URL}?service=WFS&version=1.0.0&request=GetFeature&typeName={Config.WAYPOINT_TYPE}",
        'airways': f"{Config.BASE_URL}?service=WFS&version=1.0.0&request=GetFeature&typeName={Config.AIRWAY_TYPE}",
        'vor': f"{Config.BASE_URL}?service=WFS&version=1.0.0&request=GetFeature&typeName={Config.VOR_TYPE}",
        'ndb': f"{Config.BASE_URL}?service=WFS&version=1.0.0&request=GetFeature&typeName={Config.NDB_TYPE}"
    }
    output_file = os.path.join(args.output_dir, Config.OUTPUT_FILE)
    
    try:
        # Fetch data
        logger.info("Fetching waypoint data...")
        waypoint_xml = fetch_xml(urls['waypoints'])
        logger.info("Fetching airway data...")
        airway_xml = fetch_xml(urls['airways'])
        logger.info("Fetching VOR data...")
        vor_xml = fetch_xml(urls['vor'])
        logger.info("Fetching NDB data...")
        ndb_xml = fetch_xml(urls['ndb'])
        
        # Parse data
        logger.info("Parsing waypoint data...")
        waypoints = parse_xml_safely(waypoint_xml, parse_waypoints)
        logger.info("Parsing airway data...")
        airways = parse_xml_safely(airway_xml, parse_airways, waypoints)
        logger.info("Parsing VOR data...")
        vors = parse_xml_safely(vor_xml, parse_vor)
        logger.info("Parsing NDB data...")
        ndbs = parse_xml_safely(ndb_xml, parse_ndb)
        
        # Process fixes
        fixes_in_airways = {fix for airway in airways.values() for fix in airway}
        fixes_not_in_airways = set(waypoints.keys()) - fixes_in_airways
        
        # Write combined output
        with open(output_file, 'w', encoding='utf-8') as f:
            write_output(f, waypoints, fixes_in_airways, fixes_not_in_airways, vors, ndbs)
        
        print_results(output_file, waypoints, fixes_in_airways, fixes_not_in_airways, vors, ndbs)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
