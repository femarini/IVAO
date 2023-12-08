import pandas as pd


def decimal_to_dms(decimal_degrees, direction_positive, direction_negative):
    absolute = decimal_degrees.abs()
    degrees = absolute.astype(int)
    minutes_not_truncated = (absolute - degrees) * 60
    minutes = minutes_not_truncated.astype(int)
    seconds = (minutes_not_truncated - minutes) * 60
    dms_str = (
        degrees.astype(str).str.zfill(3)
        + "."
        + minutes.astype(str).str.zfill(2)
        + "."
        + seconds.round(3).astype(str).str.zfill(6)
    )
    return dms_str.where(decimal_degrees >= 0, direction_negative + dms_str).where(
        decimal_degrees < 0, direction_positive + dms_str
    )


def meters_to_feet(meters_series):
    return (meters_series * 3.28084).round(0)


def extract_data(file_path, output_file, fir_filter):
    df = pd.read_excel(file_path)

    # Sort data by FIR and then by localidade_id
    df = df.sort_values(by=["fir", "localidade_id"])

    # Apply FIR filter based on the dictionary
    filtered_firs = {fir for fir, include in fir_filter.items() if include}
    df = df[df["fir"].isin(filtered_firs)]

    groups = df.groupby("fir")
    formatted_lines = []

    for fir, group in groups:
        group["elevacao_ft"] = meters_to_feet(group["elevacao"])
        group["latitude_dms"] = decimal_to_dms(group["latitude_dec"], "N", "S")
        group["longitude_dms"] = decimal_to_dms(group["longitude_dec"], "E", "W")
        group["suffix"] = (
            group["localidade_id"].str.startswith("SB").map({True: ";2", False: ";1"})
        )
        group_lines = group.apply(
            lambda row: f"{row['localidade_id']};{row['elevacao_ft']};0;{row['latitude_dms']};{row['longitude_dms']};{row['nome']}{row['suffix']};",
            axis=1,
        ).str.cat(sep="\n")
        formatted_lines.append(f"\n//FIR {fir}\n{group_lines}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(formatted_lines))


if __name__ == "__main__":
    file_path = "airport.xls"  # Replace with the actual file path
    output_file = "airport.txt"  # The output file path
    fir_filter = {
        "SBCW": True,
        "SBRE": True,
        "SBBS": True,
        "SBAO": True,
        "SBAZ": True,
    }  # FIR filter settings
    extract_data(file_path, output_file, fir_filter)
