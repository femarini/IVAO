import requests
import xml.etree.ElementTree as ET

# URL of the WFS service
url = "https://geoaisweb.decea.mil.br/geoserver/ICA/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ICA%3Avor"

# Function to convert GMS to S000.00.00.000 or W000.00.00.000 format
def gms_to_decimal(gms_str):
    # Split the GMS string into degrees, minutes, seconds, and hemisphere
    degrees, minutes_seconds = gms_str.split("°")
    minutes, seconds_hemisphere = minutes_seconds.split("'")
    seconds = seconds_hemisphere[:-2].replace('"', '')  # Extract seconds (without hemisphere and remove quotes)
    hemisphere = seconds_hemisphere[-1]  # Extract hemisphere (S/W)

    # Combine the GMS parts into the desired format
    formatted_str = f"{degrees.zfill(3)}.{minutes.zfill(2)}.{seconds.zfill(2)}.000"
    return f"{hemisphere}{formatted_str}"

# Send a GET request to the WFS service
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    # Parse the XML content
    root = ET.fromstring(response.content)

    # Define the namespace (adjusted to match the XML sample)
    ns = {
        'gml': 'http://www.opengis.net/gml',
        'ICA': 'http://10.32.62.212/geoserver/ICA'
    }

    # Open a file to write the output
    with open('navaid.txt', 'w') as file:
        # Find all VOR elements
        for vor in root.findall('.//ICA:vor', ns):
            ident = vor.find('ICA:ident', ns).text.strip()
            frequency = vor.find('ICA:frequency', ns).text.strip()

            # Get the GMS format latitude and longitude
            latitude_gms = vor.find('ICA:latitude_gms', ns).text.strip()
            longitude_gms = vor.find('ICA:longitude_gms', ns).text.strip()

            # Convert GMS to the required format
            latitude_formatted = gms_to_decimal(latitude_gms)
            longitude_formatted = gms_to_decimal(longitude_gms)

            # Format the output as requested
            output = f"{ident};{frequency};{latitude_formatted};{longitude_formatted};\n"
            # Write the output to the file
            file.write(output)

    print("Data has been successfully written to navaid.txt")
else:
    print(f"Failed to retrieve data. HTTP Status code: {response.status_code}")
