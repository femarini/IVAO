import pandas as pd
import re


def format_dms(dms_series):
    def format_single_dms(dms):
        parts = re.split("[^\d]+", dms.strip(" "))
        formatted_parts = [
            parts[0].zfill(3),
            parts[1].zfill(2),
            parts[2].zfill(2),
            parts[3].zfill(3),
        ]
        return f"{dms[-1]}{'.'.join(formatted_parts)}"

    return dms_series.apply(format_single_dms)


def extract_vor_data(excel_path, output_path):
    try:
        vor_data = pd.read_excel(excel_path)

        # Sort data by ident (VOR identifier)
        vor_data = vor_data.sort_values(by="ident")

        vor_data["frequency"] = vor_data["frequency"].map("{:.2f}".format)
        vor_data["latitude_formatted"] = format_dms(vor_data["latitude_gms"])
        vor_data["longitude_formatted"] = format_dms(vor_data["longitude_gms"])

        formatted_data = vor_data.apply(
            lambda x: f"{x['ident']};{x['frequency']};{x['latitude_formatted']};{x['longitude_formatted']};",
            axis=1,
        )

        with open(output_path, "w") as f:
            f.write("\n".join(formatted_data))
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    extract_vor_data("vor.xls", "vor.txt")
