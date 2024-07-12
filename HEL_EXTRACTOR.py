import requests
from bs4 import BeautifulSoup

def decimal_to_dms(decimal_degrees, direction_positive, direction_negative):
    degrees = int(abs(decimal_degrees))
    minutes_not_truncated = (abs(decimal_degrees) - degrees) * 60
    minutes = int(minutes_not_truncated)
    seconds = (minutes_not_truncated - minutes) * 60
    dms_str = (
        f"{degrees:03d}.{minutes:02d}.{seconds:06.3f}"
    )
    return f"{direction_positive}{dms_str}" if decimal_degrees >= 0 else f"{direction_negative}{dms_str}"

def meters_to_feet(meters):
    return round(meters * 3.28084)

def extract_data_from_url(url, output_file, fir_filter):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")

        airports = soup.find_all("ICA:airport_heliport")
        data = []

        for airport in airports:
            try:
                localidade_id = airport.find("ICA:localidade_id").get_text()
                elevacao = float(airport.find("ICA:elevacao").get_text())
                latitude_dec = float(airport.find("ICA:latitude_dec").get_text())
                longitude_dec = float(airport.find("ICA:longitude_dec").get_text())
                nome = airport.find("ICA:nome").get_text()
                fir = airport.find("ICA:fir").get_text()

                data.append({
                    "localidade_id": localidade_id,
                    "elevacao": elevacao,
                    "latitude_dec": latitude_dec,
                    "longitude_dec": longitude_dec,
                    "nome": nome,
                    "fir": fir
                })
            except AttributeError:
                # Handle missing attributes
                continue

        # Filter and sort data
        filtered_data = [d for d in data if fir_filter.get(d["fir"], False)]
        filtered_data.sort(key=lambda x: (x["fir"], x["localidade_id"]))

        # Process and format data
        formatted_lines = []
        current_fir = None
        for entry in filtered_data:
            if entry["fir"] != current_fir:
                current_fir = entry["fir"]
                formatted_lines.append(f"\n//FIR {current_fir}")

            elevacao_ft = meters_to_feet(entry["elevacao"])
            latitude_dms = decimal_to_dms(entry["latitude_dec"], "N", "S")
            longitude_dms = decimal_to_dms(entry["longitude_dec"], "E", "W")
            suffix = ";2" if entry["localidade_id"].startswith("SB") else ";1"

            line = f"{entry['localidade_id']};{elevacao_ft};0;{latitude_dms};{longitude_dms};{entry['nome']}{suffix};"
            formatted_lines.append(line)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(formatted_lines))
    except requests.RequestException as e:
        print(f"Error fetching data from URL: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Aairport_heliport"
    output_file = "helipads+airports.txt"  # The output file path
    fir_filter = {
        "SBCW": True,
        "SBRE": True,
        "SBBS": True,
        "SBAO": True,
        "SBAZ": True,
    }  # FIR filter settings
    extract_data_from_url(url, output_file, fir_filter)
