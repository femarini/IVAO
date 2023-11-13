import sys
from bs4 import BeautifulSoup


def extract_ctr_sectors(file_path, output_file_path):
    try:
        with open(file_path, "r") as file:
            soup = BeautifulSoup(file.read(), "xml")

        sectors = soup.find_all("ICA:CTR")
        formatted_data = []

        for sector in sectors:
            name = sector.find("ICA:nam")
            coordinates_data = sector.find("gml:coordinates")
            related_fir = sector.find("ICA:relatedfir")

            if name and coordinates_data:
                name_text = name.get_text()
                coordinate_pairs = coordinates_data.get_text().split()
                related_fir_text = f";//{related_fir.get_text()}" if related_fir else ""
                sector_data = [
                    f"{'T;'}CTR {name_text};{lon};{lat}{related_fir_text}"
                    for i, (lat, lon) in enumerate(
                        pair.split(",") for pair in coordinate_pairs
                    )
                ]
                formatted_data.append((name_text, sector_data))

        formatted_data.sort(key=lambda x: x[0])

        with open(output_file_path, "w", encoding="utf-8") as output_file:
            output_file.writelines(
                "\n".join(
                    line for _, sector_data in formatted_data for line in sector_data
                )
                + "\n"
            )

        print(
            f"CTR sectors extracted and sorted alphabetically and saved to {output_file_path}"
        )

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    extract_ctr_sectors("ctr.xml", "ctr.txt")
