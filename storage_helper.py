import file_helper
import csv

def write_to_csv(data: dict, output_path: str) -> None:
    """
    Write data to a CSV file, ensuring it is sorted by frame number.

    Args:
        data (dict): A dictionary where keys are frame numbers and values are lists of track data.
        output_path (str): The path to the output CSV file.
    """
    # make sure data is sorted
    sorted_data = {k: data[k] for k in sorted(data.keys())}
    with open(output_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['FRAME_NUMBER', 'ID', 'CONFIDENCE', 'X1', 'Y1', 'X2', 'Y2'])
        for frame_num, tracks in sorted_data.items():
            if len(tracks) == 0:
                writer.writerow([frame_num])
            for track in tracks:
                writer.writerow([frame_num, *track])

def read_from_csv(input_path: str) -> dict:
    """
    Read data from a CSV file and return it as a dictionary.

    Args:
        input_path (str): The path to the input CSV file.

    Returns:
        dict: A dictionary where keys are frame numbers and values are lists of track data.
    """
    data = {}
    with open(input_path, 'r', newline='') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row
        for row in reader:
            if len(row) == 1:
                data[int(row[0])] = []
                continue
            frame_number, id, confidence, x1, y1, x2, y2 = row
            frame_number, id, x1, y1, x2, y2 = int(frame_number), int(id), float(x1), float(y1), float(x2), float(y2)
            confidence = None if confidence == '' else float(confidence)
            if frame_number not in data.keys():
                data[frame_number] = []
            data[frame_number].append( (id, confidence, x1, y1, x2, y2) )
    return data

def find_raw_data(video_path: str) -> str:
    """
    Find the path to the raw CSV file of a given video.

    Args:
        video_path (str): The path to the video file.

    Returns:
        str: The path to the raw CSV file if it exists, otherwise None.
    """
    raw_csv = f'{get_prepared_path(video_path)}_raw.csv'
    return raw_csv if file_helper.check_existance(raw_csv) else None

def get_prepared_path(video_path: str) -> str:
    """
    Get the prepared path by splitting the video path into directory and filename.

    Args:
        video_path (str): The path to the video file.

    Returns:
        str: The prepared path without the file extension.
    """
    directory, filename, extension = file_helper.split_path(video_path)
    return file_helper.join_paths(directory, filename)
