import sys
from bs4 import BeautifulSoup


def extract_tma_sectors(file_path, output_file_path):
    try:
        with open(file_path, "r") as file:
            soup = BeautifulSoup(file.read(), "xml")

        sectors = soup.find_all("ICA:TMA")
        formatted_data = []

        for sector in sectors:
            ident = sector.find("ICA:ident")
            coordinates_data = sector.find("gml:coordinates")

            if ident and coordinates_data:
                ident_text = ident.get_text()
                coordinate_pairs = coordinates_data.get_text().split()
                sector_data = [
                    f"{'T;' if i else 'T;'}{ident_text};{lon};{lat};"
                    for i, (lat, lon) in enumerate(
                        pair.split(",") for pair in coordinate_pairs
                    )
                ]
                formatted_data.append((ident_text, sector_data))

        formatted_data.sort(key=lambda x: x[0])

        with open(output_file_path, "w") as output_file:
            output_file.writelines(
                "\n".join(
                    line for _, sector_data in formatted_data for line in sector_data
                )
                + "\n"
            )

        print(
            f"TMA sectors extracted and sorted alphabetically and saved to {output_file_path}"
        )

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    extract_tma_sectors("tma.xml", "tma.txt")
