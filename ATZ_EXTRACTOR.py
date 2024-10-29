import os
import requests
from bs4 import BeautifulSoup
from geopy.distance import geodesic
from shapely.geometry import LineString
from collections import defaultdict

def extract_atz_sectors_from_url(url, output_file_name, tolerance=0.001):
    """Extracts ATZ sectors from a GML URL, simplifies coordinates, and saves them to a text file on the desktop."""
    def simplify_coordinates(coords, tolerance):
        """Simplifies a list of coordinates using Shapely's simplify method."""
        line = LineString(coords)
        simplified_line = line.simplify(tolerance, preserve_topology=False)
        return list(simplified_line.coords)

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")

        sectors = soup.find_all("ICA:ATZ")
        fir_sectors = defaultdict(list)  # Dict to group sectors by FIR

        for sector in sectors:
            name = sector.find("ICA:nam")
            coordinates_data = sector.find("gml:coordinates")
            related_fir = sector.find("ICA:relatedfir")

            if name and coordinates_data:
                name_text = name.get_text()
                coordinate_pairs = coordinates_data.get_text().split()
                related_fir_text = f"{related_fir.get_text()}" if related_fir else ""

                # Extract coordinates as tuples of floats, correctly ordered
                coordinates = [(float(lat), float(lon)) for lon, lat in (pair.split(",") for pair in coordinate_pairs)]
                
                # Simplify coordinates
                simplified_coordinates = simplify_coordinates(coordinates, tolerance)

                # Format the simplified coordinates
                sector_data = [
                    f"T;ATZ {name_text};{lat};{lon};"
                    for lat, lon in simplified_coordinates
                ]

                fir_sectors[related_fir_text].extend(sector_data)

        # Get the user's desktop path
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        output_file_path = os.path.join(desktop_path, output_file_name)

        # Check if the desktop path is valid and writable
        if not os.access(desktop_path, os.W_OK):
            raise PermissionError(f"The desktop directory is not writable: {desktop_path}")

        # Sort sectors within each FIR and write to file
        with open(output_file_path, "w", encoding="utf-8") as output_file:
            for fir, sector_list in fir_sectors.items():
                output_file.write(f"//FIR {fir}\n")
                output_file.writelines("\n".join(sector_list) + "\n")

        print(f"ATZ sectors extracted, simplified, and grouped by FIR, saved to {output_file_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3AATZ"
    extract_atz_sectors_from_url(url, "atz.txt")
