import logging, traceback, json, csv
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# set up logging
logging.basicConfig(
    filename=Path('aggregation_error_log.log'),
    filemode='a',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# quadruple field size limit (default=131_072)
csv.field_size_limit(524288)


def select_directory():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title='Select the Root Directory')



def collect_csv_files(base_path):
    """
    Collects all CSV files from the given base path and its subdirectories.

    Args:
        base_path (Path): The root directory to search for CSV files.

    Returns:
        List[Path]: List of paths to CSV files.
    """
    return list(base_path.rglob('extracted_datapoints.csv'))

def read_csv_file(file_path):
    """
    Reads a CSV file and returns its content as a list of dictionaries.

    Args:
        file_path (Path): The path to the CSV file.

    Returns:
        List[dict]: List of rows as dictionaries.
    """
    with file_path.open('r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        return list(reader)

def aggregate_csv_data(csv_files):
    """
    Aggregates data from multiple CSV files into a dictionary grouped by video name.

    Args:
        csv_files (List[Path]): List of paths to CSV files.

    Returns:
        dict: Aggregated data grouped by video name.
    """
    grouped_data = {}
    for file_path in csv_files:
        try:
            data = read_csv_file(file_path)
            video_name = Path(data[0]['Video Name']).stem
            if video_name not in grouped_data:
                grouped_data[video_name] = []
            grouped_data[video_name].extend(data)
        except Exception as e:
            logging.error(f'Error reading {file_path}: {e}')
    return grouped_data

def save_as_json(data, output_path):
    """
    Saves the aggregated data to a JSON file.

    Args:
        data (dict): The aggregated data to save.
        output_path (Path): The path to the output JSON file.
    """
    with output_path.open('w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

def main(base_path, output_file):
    """
    Main function to aggregate all CSV files in a directory tree and save as JSON.

    Args:
        base_path (str): The root directory to search for CSV files.
        output_file (str): The path to the output JSON file.
    """
    base_path = Path(base_path)
    output_file = Path(output_file)

    print(f'Collecting CSV files from {base_path}...')
    csv_files = collect_csv_files(base_path)

    print(f'Found {len(csv_files)} CSV files. Aggregating data...')
    aggregated_data = aggregate_csv_data(csv_files)

    print(f'Saving aggregated data to {output_file}...')
    save_as_json(aggregated_data, output_file)

    print('Aggregation complete.')

if __name__ == '__main__':
    root_path = None
    while not root_path:
        root_path = select_directory()
    
    try:
        main(root_path, 'aggregated.json')
    except Exception as err:
        logging.error(f'Unhandled exception occurred:\n{traceback.format_exc()}')
        print('An unexpected error occurred. Please check the log file for details.')
