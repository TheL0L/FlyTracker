import file_helper, storage_helper
import csv
import re
import numpy as np
import cv2

__PX2CM = 1 / 25


def convert_px_to_cm(length: float) -> float:
    return length * __PX2CM

def convert_point_px_to_cm(point: tuple[float, float]) -> tuple[float, float]:
    return convert_px_to_cm(point[0]), convert_px_to_cm(point[1])

def convert_pxpf_to_cmps(speed: float, frame_rate: float) -> float:
    return convert_px_to_cm(speed) * frame_rate

def invert_yaxis(point: tuple[float, float], height: int) -> tuple[float, float]:
    return (point[0], height - point[1])

def write_to_csv(findings: dict, extra_data: dict, output_path: str) -> None:
    # if file doesn't exist yet, create it and write headers to it
    if not file_helper.check_existance(output_path):
        with open(output_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
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
                'Total Frames',
                'Time [sec]',
                'Start Position (x, y)[cm, cm]',
                'End Position (x, y)[cm, cm]',
                'Distance [cm]',
                'Min Speed [cm/sec]',
                'Max Speed [cm/sec]',
                'Avg Speed [cm/sec]',
                'Median Speed [cm/sec]',
                'Positions (x, y)[cm, cm]'
            ])

    # write findings to the file
    with open(output_path, 'a', newline='') as file:
        writer = csv.writer(file)
        for ID in findings.keys():
            writer.writerow([
                extra_data['Video Name'],
                extra_data['Age'],
                extra_data['Mating Date'],
                extra_data['Testing Date'],
                extra_data['Group'],
                extra_data['Technical Repetition'],
                extra_data['Vial Number'],
                ID,
                findings[ID]['first_frame'],
                findings[ID]['last_frame'],
                findings[ID]['total_frames'],
                findings[ID]['time'],
                findings[ID]['start_position'],
                findings[ID]['end_position'],
                findings[ID]['distance'],
                findings[ID]['min_speed'],
                findings[ID]['max_speed'],
                findings[ID]['avg_speed'],
                findings[ID]['med_speed'],
                findings[ID]['positions']
            ])

    return

def decompose_path(path: str) -> dict:
    norm_path = file_helper.normalize_path(path)

    directory, filename, extension = file_helper.split_path(path)

    result = {
        'Video Name':           filename + extension,
        'Age':                  None,
        'Mating Date':          None,
        'Testing Date':         None,
        'Group':                None,
        'Technical Repetition': None,
        'Vial Number':          None,
    }
    regex = re.compile(r'.*NGT-SCE/NGT_mating_\d+\.\d+\.\d+/(\d+)d(\d{8})_(\d{8})_NGT/.+/(\d+)_\d{8}_1\.(\d+)_start_v([1-5])\.avi$')

    m = regex.match(norm_path)
    if m is None:
        return None

    date_format = lambda date: f'{date[:2]}/{date[2:4]}/{date[4:]}'

    g = m.groups()
    result['Age']                  = int(g[0])
    result['Mating Date']          = date_format(g[1])
    result['Testing Date']         = date_format(g[2])
    result['Group']                = int(g[3])
    result['Technical Repetition'] = int(g[4])
    result['Vial Number']          = int(g[5])

    return result

