import logging, traceback, re, csv
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# set up logging
logging.basicConfig(
    filename=Path('fix_error_log.log'),
    filemode='a',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# quadruple field size limit (default=131_072)
csv.field_size_limit(524288)

# define the columns order to be used
FIELDNAMES = [
    'Video Name',
    'Age',
    'Mating Date',
    'Testing Date',
    'Group',
    'Technical Repetition',
    'Vial Number',
    'ID',
    'First Frame',
    'Last Frame',
    'Total Frames',                    # recalculate using first,last frames. old calculation was off by 1 due to missing the 0th frame
    'Time [sec]',                      # recalculate using correct frame count. at 30fps the old calculation was off by 1/30[sec] ~ 0.03[sec]
    'Start Position (x, y)[cm, cm]',
    'End Position (x, y)[cm, cm]',
    'Distance [cm]',
    'Upwards Distance [cm]',           # some csv files don't have this metric
    'Max Height [cm]',                 # some csv files don't have this metric, those that have it are missing the px->cm conversion
    'Max Height Frame',                # some csv files don't have this metric
    'Max Height Time [sec]',           # some csv files don't have this metric
    'Min Speed [cm/sec]',              # instanteneous speeds were mistakenly divided by 2
    'Max Speed [cm/sec]',              # instanteneous speeds were mistakenly divided by 2
    'Avg Speed [cm/sec]',              # instanteneous speeds were mistakenly divided by 2, now instead of using the 'arithmetic mean' use 'distance/time average'
    'Arithmetic Mean Speed [cm/sec]',  # instanteneous speeds were mistakenly divided by 2
    'Median Speed [cm/sec]',           # instanteneous speeds were mistakenly divided by 2
    'Positions (x, y)[cm, cm]',
    'Treatment'                        # some csv files don't have this metric, unless this field exists and has a value, try to infer its value using the existing regex
]



def select_directory():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title='Select the Root Directory')


def decompose_path(path):
    """
    Decompose a given file path into its constituent parts and extract metadata.

    Args:
        path (str): The file path to decompose.

    Returns:
        dict: A dictionary containing the decomposed path and extracted metadata.
    """
    norm_path = Path(path).resolve().as_posix()

    result = {
        'Treatment':            None,
        'Video Name':           Path(path).name,
        'Age':                  None,
        'Mating Date':          None,
        'Testing Date':         None,
        'Group':                None,
        'Technical Repetition': None,
        'Vial Number':          None,
    }

    root = r'.*NGT-SCE/NGT_mating_'
    root_mating_date = r'\d+\.\d+\.\d+'
    age = r'\d+'
    mating_date = r'\d{8}'
    testing_date = r'\d{8}'
    any_folder = r'.+'
    group = r'\d+'
    constant_number = r'\d+'
    technical_repetition = r'\d+'
    vial_number = r'[1-5]'

    regex_pattern = rf'{root}{root_mating_date}/({age})d({mating_date})_({testing_date})_NGT/({any_folder})/' \
                    rf'({group})_{testing_date}_{constant_number}\.({technical_repetition})_start_v({vial_number})\.avi$'
    
    regex = re.compile(regex_pattern)

    m = regex.match(norm_path)
    if m is None:
        result['Video Name'] = norm_path
        return result

    date_format = lambda date: f'{date[:2]}/{date[2:4]}/{date[4:]}'

    g = m.groups()
    result['Age']                  = int(g[0])
    result['Mating Date']          = date_format(g[1])
    result['Testing Date']         = date_format(g[2])
    result['Treatment']            = g[3]
    result['Group']                = int(g[4])
    result['Technical Repetition'] = int(g[5])
    result['Vial Number']          = int(g[6])

    return result


def extract_data(data, frame_rate):
    findings = {
        'upwards_distance': None, 'max_height': None, 'max_height_frame': None, 'max_height_time': None
    }

    positions = eval(data['Positions (x, y)[cm, cm]'])

    # calculate travel distance and max height
    upwards_distance = 0
    max_height = 0
    max_height_frame = 0
    for i in range(1, len(positions)):
        x1, y1 = positions[i - 1]
        x2, y2 = positions[i]

        # update max height
        if y2 > max_height:
            max_height = y2
            max_height_frame = i

        # update upwards movement
        if y2 > y1:
            upwards_distance += y2 - y1

    findings['upwards_distance'] = upwards_distance
    findings['max_height'] = max_height

    # calculate time taken to reach max height
    findings['max_height_frame'] = int(data['First Frame']) + max_height_frame
    findings['max_height_time'] = findings['max_height_frame'] / frame_rate

    return findings



def collect_csv_files(base_path):
    return list(base_path.rglob("extracted_datapoints.csv"))

def read_csv_file(file_path):
    with file_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)

def write_csv_file(file_path, data):
    with file_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(data)

def approximate_framerate(data):
    frame_rate = int(data['Total Frames']) / float(data['Time [sec]'])
    return round(frame_rate)

def validate_total_frames(data, frame_rate):
    correct_frames = int(data['Last Frame']) - int(data['First Frame']) + 1
    correct_time = correct_frames / frame_rate
    data['Total Frames'] = correct_frames
    data['Time [sec]'] = correct_time
    return data

def validate_treatment(data, file_path):
    video_path = Path(file_path).parent.joinpath(Path(data['Video Name']).name)
    treatment = decompose_path(video_path)['Treatment']
    treatment = treatment if treatment is None else treatment.split('/')[0]
    if 'Treatment' in data and data['Treatment'] is None:
        data['Treatment'] = treatment
    return data

def validate_vertical_stats(data, frame_rate):
    findings = extract_data(data, frame_rate)
    data['Upwards Distance [cm]'] = findings['upwards_distance']
    data['Max Height [cm]'] = findings['max_height']
    data['Max Height Frames'] = findings['max_height_frame']  # this will be renamed later since it might exist already
    data['Max Height Time [sec]'] = findings['max_height_time']
    return data

def rename_max_height_frame(data):
    data['Max Height Frame'] = data.pop('Max Height Frames')
    return data

def validate_speed_stats(data):
    data['Min Speed [cm/sec]'] = float(data['Min Speed [cm/sec]']) * 2
    data['Max Speed [cm/sec]'] = float(data['Max Speed [cm/sec]']) * 2
    data['Arithmetic Mean Speed [cm/sec]'] = float(data['Avg Speed [cm/sec]']) * 2
    data['Median Speed [cm/sec]'] = float(data['Median Speed [cm/sec]']) * 2
    data['Avg Speed [cm/sec]'] = float(data['Distance [cm]']) / data['Time [sec]']
    return data

def main(base_path):
    base_path = Path(base_path)

    print(f'Collecting CSV files from {base_path}...')
    csv_files = collect_csv_files(base_path)

    print(f'Found {len(csv_files)} CSV files. Validating data...')
    for file_path in csv_files:
        try:
            data = read_csv_file(file_path)
        except Exception as err:
            logging.error(f'Error reading {file_path}: {err}')
            continue

        try:
            frame_rate = approximate_framerate(data[0])
            validated_data = []
            for entry in data:
                entry = validate_total_frames(entry, frame_rate)
                entry = validate_treatment(entry, file_path)
                entry = validate_vertical_stats(entry, frame_rate)
                entry = rename_max_height_frame(entry)
                entry = validate_speed_stats(entry)
                validated_data.append(entry)
        except Exception as err:
            logging.error(f'Error modifying the data: {err}')
            continue

        try:
            write_csv_file(file_path, validated_data)
        except Exception as err:
            logging.error(f'Error writing {file_path}: {err}')
            continue

    print('Validation complete.')

if __name__ == '__main__':
    root_path = None
    while not root_path:
        root_path = select_directory()
    
    try:
        main(root_path)
    except Exception as err:
        logging.error(f'Unhandled exception occurred:\n{traceback.format_exc()}')
        print('An unexpected error occurred. Please check the log file for details.')
