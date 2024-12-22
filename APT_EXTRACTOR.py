import os
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

def extract_data_from_url(url, output_file, fir_filter, tipo_util_filter):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")
        airports = soup.find_all("ICA:airport")
        data = []
        for airport in airports:
            try:
                localidade_id = airport.find("ICA:localidade_id").get_text()
                elevacao = float(airport.find("ICA:elevacao").get_text())
                latitude_dec = float(airport.find("ICA:latitude_dec").get_text())
                longitude_dec = float(airport.find("ICA:longitude_dec").get_text())
                nome = airport.find("ICA:nome").get_text()
                fir = airport.find("ICA:fir").get_text()
                tipo_util = airport.find("ICA:tipo_util").get_text()
                
                # Apply FIR and tipo_util filters
                if (not fir_filter or fir in fir_filter) and tipo_util in tipo_util_filter:
                    data.append({
                        "localidade_id": localidade_id,
                        "elevacao": elevacao,
                        "latitude_dec": latitude_dec,
                        "longitude_dec": longitude_dec,
                        "nome": nome,
                        "fir": fir,
                        "tipo_util": tipo_util
                    })
            except AttributeError:
                # Handle missing attributes
                continue
        
        # Sort data
        data.sort(key=lambda x: (x["fir"], x["localidade_id"]))
        
        # Define mapping for tipo_util to number
        tipo_util_to_number = {
            "PRIV": 3,
            "PUB/MIL": 0,
            "PUB": 0,
            "PRIV/PUB": 3,
            "MIL": 2,
            "PUB/REST": 0
        }

        tipo_util_to_suffix = {
            "PRIV": 1,
            "PUB/MIL": 2,
            "PUB": 2,
            "PRIV/PUB": 2,
            "MIL": 2,
            "PUB/REST": 2
        }

        # Process and format data
        formatted_lines = []
        current_fir = None
        for entry in data:
            if entry["fir"] != current_fir:
                current_fir = entry["fir"]
                if formatted_lines:
                    formatted_lines.append(f"//FIR {current_fir}")
                else:
                    formatted_lines.append(f"//FIR {current_fir}")
            try:
                elevacao_ft = meters_to_feet(entry["elevacao"])
                latitude_dms = decimal_to_dms(entry["latitude_dec"], "N", "S")
                longitude_dms = decimal_to_dms(entry["longitude_dec"], "E", "W")
                suffix_number = tipo_util_to_suffix.get(entry["tipo_util"], 1)
                suffix = f";{suffix_number}"

                # Get the number for tipo_util
                tipo_util_number = tipo_util_to_number.get(entry["tipo_util"], 0)

                line = (f"{entry['localidade_id']};{elevacao_ft};0;"
                        f"{latitude_dms};{longitude_dms};{entry['nome']}{suffix};{tipo_util_number};")
                formatted_lines.append(line)
            except KeyError as e:
                print(f"Error formatting entry {entry}: Missing key {e}")
            except Exception as e:
                print(f"Unexpected error formatting entry {entry}: {e}")
        
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(formatted_lines))
        except IOError as e:
            print(f"Error writing to file {output_file}: {e}")
    except requests.RequestException as e:
        print(f"Error fetching data from URL: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Aairport"
    
    # Set output file path to Desktop
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    output_file = os.path.join(desktop_path, "airport.txt")
    
    # FIR filter settings
    # Set to None for all FIRs, or specify a set of FIRs to filter
    fir_filter = {"SBCW", "SBBS", "SBAZ", "SBRE", "SBAO"}
    # Uncomment the next line to include all FIRs
    # fir_filter = None
    
    tipo_util_filter = {"PRIV", "PUB/MIL", "PUB", "PRIV/PUB", "MIL", "PUB/REST"}  # tipo_util filter
    extract_data_from_url(url, output_file, fir_filter, tipo_util_filter)
