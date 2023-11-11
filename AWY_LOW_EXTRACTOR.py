import pandas as pd


def format_lines_with_repetition(group, prefix):
    lines = []
    for index, row in group.iterrows():
        from_ident = row["from_fix_ident"]
        to_ident = row["to_fix_ident"]

        # Format the 'from' line with the 'from_fix_ident' repeated
        from_line = f"{prefix};{row['text_designator']};{from_ident};{from_ident};"
        lines.append(from_line)

        # Format the 'to' line with the 'to_fix_ident' repeated
        to_line = f"{prefix};{row['text_designator']};{to_ident};{to_ident};"
        lines.append(to_line)

    return lines


def check_airway_sequence(df):
    # Ensure the DataFrame is sorted by 'gid' and 'sequence'
    df = df.sort_values(by=["gid", "sequence"])

    errors = []  # List to hold any sequence errors found

    # Iterate over each airway group
    for gid, group in df.groupby("gid"):
        last_to_fix_ident = None

        # Iterate over each row in the group
        for idx, row in group.iterrows():
            # If this is not the first row in the group, check the sequence
            if (
                last_to_fix_ident is not None
                and last_to_fix_ident != row["from_fix_ident"]
            ):
                # If the sequence is incorrect, record the error
                errors.append(
                    f"Sequence error at gid {gid}, index {idx}: {last_to_fix_ident} -> {row['from_fix_ident']}"
                )

            # Update the last to_fix_ident for the next iteration
            last_to_fix_ident = row["to_fix_ident"]

    return errors


def extract_and_format_airways(file_path, output_file):
    # Load the Excel file
    xls = pd.ExcelFile(file_path)

    # Read the first sheet or a specific sheet if needed
    df = xls.parse(0)

    # Sort by airway name (text_designator) first, then by sequence within each airway name
    df.sort_values(by=["text_designator", "sequence"], inplace=True)

    # Check the airway sequence before proceeding with formatting
    sequence_errors = check_airway_sequence(df)
    if sequence_errors:
        # If there are errors, print them and exit the function
        for error in sequence_errors:
            print(error)
        return  # Stop the function if there are sequence errors

    # Group by 'text_designator' to maintain the order by airway name
    grouped_data = df.groupby("text_designator")

    t_lines = []
    l_lines = []

    # Initialize variables to keep track of the last line added for T and L
    last_t_line = None
    last_l_line = None

    # Within each airway name, process each group maintaining the right sequence
    for airway_name, group in grouped_data:
        # Format the lines for this airway group with T prefix
        formatted_t_lines = format_lines_with_repetition(group, "T")
        # Format the lines for this airway group with L prefix
        formatted_l_lines = format_lines_with_repetition(group, "L")

        # Add lines to the output list, avoiding consecutive duplicates for T
        for line in formatted_t_lines:
            if line != last_t_line:
                t_lines.append(line)
                last_t_line = line  # Update the last line for T

        # Add lines to the output list, avoiding consecutive duplicates for L
        for line in formatted_l_lines:
            if line != last_l_line:
                l_lines.append(line)
                last_l_line = line  # Update the last line for L

    # Write the formatted "T;" and "L;" lines to the output file
    with open(output_file, "w") as file:
        for line in t_lines + l_lines:  # Concatenate T and L lines
            file.write(line + "\n")


if __name__ == "__main__":
    # The path to the Excel file and the output text file
    file_path = "vw_aerovia_baixa_v2.xls"
    output_file = "awy_low.txt"
    extract_and_format_airways(file_path, output_file)
