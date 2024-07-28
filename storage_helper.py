import file_helper
import csv

def write_to_csv(data: dict, output_path: str):
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
    data = {}
    with open(input_path, 'r', newline='') as file:
        reader = csv.reader(file)
        next(reader)
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
    """Find a path to the raw csv of a given video."""
    raw_csv = f'{get_prepared_path(video_path)}_raw.csv'
    return raw_csv if file_helper.check_existance(raw_csv) else None

def get_prepared_path(video_path: str) -> str:
    directory, filename, extension = file_helper.split_path(video_path)
    return file_helper.join_paths(directory, filename)
