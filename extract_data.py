import file_helper, storage_helper
import csv
import re
import numpy as np
import cv2

__PX2CM = 1 / 25


def convert_px_to_cm(length: float) -> float:
    """
    Convert length from pixels to centimeters.
    
    Args:
        length (float): Length in pixels.

    Returns:
        float: Length in centimeters.
    """
    return length * __PX2CM

def convert_point_px_to_cm(point: tuple[float, float]) -> tuple[float, float]:
    """
    Convert a point's coordinates from pixels to centimeters.
    
    Args:
        point (tuple[float, float]): A tuple containing the x and y coordinates in pixels.

    Returns:
        tuple[float, float]: A tuple containing the x and y coordinates in centimeters.
    """
    return convert_px_to_cm(point[0]), convert_px_to_cm(point[1])

def convert_pxpf_to_cmps(speed: float, frame_rate: float) -> float:
    """
    Convert speed from pixels per frame to centimeters per second.
    
    Args:
        speed (float): Speed in pixels per frame.
        frame_rate (float): Frame rate of the video.

    Returns:
        float: Speed in centimeters per second.
    """
    return convert_px_to_cm(speed) * frame_rate

def invert_yaxis(point: tuple[float, float], height: int) -> tuple[float, float]:
    """
    Invert the y-axis of a point's coordinates.
    
    Args:
        point (tuple[float, float]): A tuple containing the x and y coordinates.
        height (int): Height of the frame or image.

    Returns:
        tuple[float, float]: A tuple containing the x and y coordinates with the y-axis inverted.
    """
    return (point[0], height - point[1])

def write_to_csv(findings: dict, extra_data: dict, output_path: str) -> None:
    """
    Write findings and extra data to a CSV file.
    
    Args:
        findings (dict): A dictionary containing findings data.
        extra_data (dict): A dictionary containing extra data.
        output_path (str): The path to the output CSV file.
    """
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
    """
    Decompose a given file path into its constituent parts and extract metadata.

    Args:
        path (str): The file path to decompose.

    Returns:
        dict: A dictionary containing the decomposed path and extracted metadata.
    """
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

def extract_findings(results_csv_path: str) -> None:
    """
    Extract findings from a CSV file and write the results to a new CSV file.

    Args:
        results_csv_path (str): The path to the CSV file containing results data.
    """
    # read and parse available data
    video_path = results_csv_path.replace('_result.csv', '.avi')
    data = storage_helper.read_from_csv(results_csv_path)
    data_from_video_path = decompose_path(video_path)

    # prepare export filepath
    directory, filename, extension = file_helper.split_path(results_csv_path)
    export_path = file_helper.join_paths(directory, 'extracted_datapoints.csv')

    # find the video frame rate and dimensions
    try:
        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened:
            raise Exception()
        frame_rate = int(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        capture.release()
    except:
        frame_rate = 30
        width = 70
        height = 420
        print(f'Could not read video at {video_path}')
        print(f'assigning default values {frame_rate=}  {width=}  {height=}')

    # prepare dictionary to store data points on flies
    # find all qunique IDs whithin the available data
    findings = {}
    for frame_number, tracks in data.items():
        for track in tracks:
            id, conf, x1, y1, x2, y2 = track
            _position = ( (x1 + x2)/2, (y1 + y2)/2 )
            if id not in findings.keys():
                findings[id] = {
                    'first_frame': frame_number, 'last_frame': None, 'total_frames': None,
                    'time': None, 'start_position': _position, 'end_position': None,
                    'positions': [], 'distance': None, 'min_speed': None,
                    'max_speed': None, 'avg_speed': None, 'med_speed': None
                }
            findings[id]['last_frame'] = frame_number
            findings[id]['end_position'] = _position
            findings[id]['positions'].append(_position)

    for id in findings.keys():
        # invert y-axis for future convenience
        positions = [invert_yaxis(point, height) for point in findings[id]['positions']]
        findings[id]['start_position'] = invert_yaxis(findings[id]['start_position'], height)
        findings[id]['end_position'] = invert_yaxis(findings[id]['end_position'], height)

        # calculate the speeds and travel distance
        total_distance = 0
        speeds = []
        for i in range(1, len(positions)):
            # calculate the Euclidean distance between consecutive points
            x1, y1 = positions[i - 1]
            x2, y2 = positions[i]
            distance = np.sqrt( (x2 - x1)**2 + (y2 - y1)**2 )
            speeds.append(distance / 2)
            total_distance += distance
        
        findings[id]['min_speed'] = np.min(speeds)
        findings[id]['max_speed'] = np.max(speeds)
        findings[id]['avg_speed'] = np.mean(speeds)
        findings[id]['med_speed'] = np.median(sorted(speeds))
        findings[id]['distance']  = total_distance

        # calculate total frames and time
        findings[id]['total_frames'] = findings[id]['last_frame'] - findings[id]['first_frame']
        findings[id]['time'] = findings[id]['total_frames'] / frame_rate

        ## perform conversions
        
        # (x, y)[px, px] -> (x, y)[cm, cm]
        findings[id]['start_position']  = convert_point_px_to_cm(findings[id]['start_position'])
        findings[id]['end_position']  = convert_point_px_to_cm(findings[id]['end_position'])
        findings[id]['positions'] = [convert_point_px_to_cm(pos) for pos in positions]

        # [px/frame] ->  [cm/sec]
        findings[id]['min_speed'] = convert_pxpf_to_cmps(findings[id]['min_speed'], frame_rate)
        findings[id]['max_speed'] = convert_pxpf_to_cmps(findings[id]['max_speed'], frame_rate)
        findings[id]['avg_speed'] = convert_pxpf_to_cmps(findings[id]['avg_speed'], frame_rate)
        findings[id]['med_speed'] = convert_pxpf_to_cmps(findings[id]['med_speed'], frame_rate)

        # [px] -> [cm]
        findings[id]['distance']  = convert_px_to_cm(findings[id]['distance'])

    # export findings
    write_to_csv(findings, data_from_video_path, export_path)

