import requests
from bs4 import BeautifulSoup
import math

def extract_cta_sectors_from_url(url, output_file_path, tolerance=0.01):
    """Extracts CTA sectors from a GML URL, simplifies coordinates, and saves them to a text file."""
    def haversine(lat1, lon1, lat2, lon2):
        # Calculate the great-circle distance between two points
        R = 6371  # Earth radius in kilometers
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def simplify_coordinates(coords, tolerance):
        """Simplifies a list of coordinates using a tolerance in degrees."""
        def perpendicular_distance(point, start, end):
            """Calculate the perpendicular distance from `point` to the line defined by `start` and `end`."""
            if start == end:
                return haversine(point[0], point[1], start[0], start[1])
            x0, y0 = point
            x1, y1 = start
            x2, y2 = end
            num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
            denom = math.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)
            return num / denom

        def rdp(points, epsilon):
            """Ramer-Douglas-Peucker algorithm to reduce points."""
            if len(points) < 3:
                return points
            start, end = points[0], points[-1]
            max_dist = 0
            index = 0
            for i in range(1, len(points) - 1):
                dist = perpendicular_distance(points[i], start, end)
                if dist > max_dist:
                    index = i
                    max_dist = dist
            if max_dist > epsilon:
                results1 = rdp(points[:index + 1], epsilon)
                results2 = rdp(points[index:], epsilon)
                return results1[:-1] + results2
            else:
                return [start, end]

        return rdp(coords, tolerance)

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")

        sectors = soup.find_all("ICA:CTA")
        fir_sectors = {}  # Dict to group sectors by FIR

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
                    f"T;CTA {name_text};{lat};{lon};"
                    for lat, lon in simplified_coordinates
                ]

                if related_fir_text in fir_sectors:
                    fir_sectors[related_fir_text].extend(sector_data)
                else:
                    fir_sectors[related_fir_text] = sector_data

        # Sort sectors within each FIR and write to file
        with open(output_file_path, "w", encoding="utf-8") as output_file:
            for fir, sector_list in fir_sectors.items():
                output_file.write(f"\n\n//FIR {fir}\n")
                output_file.writelines("\n".join(sector_list) + "\n")

        print(f"CTA sectors extracted, simplified, and grouped by FIR, saved to {output_file_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3ACTA"
    extract_cta_sectors_from_url(url, "cta.txt")
