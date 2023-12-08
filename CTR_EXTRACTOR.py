import sys
from bs4 import BeautifulSoup


def extract_ctr_sectors(file_path, output_file_path):
    """Extracts CTR sectors from an XML file and saves them to a text file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file.read(), "xml")

        sectors = soup.find_all("ICA:CTR")
        fir_sectors = {}  # Dict to group sectors by FIR

        for sector in sectors:
            name = sector.find("ICA:nam")
            coordinates_data = sector.find("gml:coordinates")
            related_fir = sector.find("ICA:relatedfir")

            if name and coordinates_data:
                name_text = name.get_text()
                coordinate_pairs = coordinates_data.get_text().split()
                related_fir_text = f"{related_fir.get_text()}" if related_fir else ""

                sector_data = [
                    f"{'T;'}CTR {name_text};{lon};{lat};"
                    for i, (lat, lon) in enumerate(
                        pair.split(",") for pair in coordinate_pairs
                    )
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

        print(f"CTR sectors extracted and grouped by FIR, saved to {output_file_path}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    extract_ctr_sectors("ctr.xml", "ctr.txt")
