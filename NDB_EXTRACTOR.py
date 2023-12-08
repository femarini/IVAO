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


def extract_ndb_data(excel_path, output_path):
    try:
        ndb_data = pd.read_excel(excel_path)

        # Sort data by codeid (NDB identifier)
        ndb_data = ndb_data.sort_values(by="codeid")

        ndb_data["valfreq"] = ndb_data["valfreq"].map("{:.1f}".format)
        ndb_data["latitude_formatted"] = format_dms(ndb_data["latitude_gms"])
        ndb_data["longitude_formatted"] = format_dms(ndb_data["longitude_gms"])

        formatted_data = ndb_data.apply(
            lambda x: f"{x['codeid']};{x['valfreq']};{x['latitude_formatted']};{x['longitude_formatted']};",
            axis=1,
        )

        with open(output_path, "w") as f:
            f.write("\n".join(formatted_data))
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    extract_ndb_data("ndb.xls", "ndb.txt")
