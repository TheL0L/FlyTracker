import file_helper
import csv
import re

def write_to_csv(data: dict, output_path: str):
    with open(output_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['FRAME_NUMBER', 'ID', 'CONFIDENCE', 'X1', 'Y1', 'X2', 'Y2'])
        for frame_num, tracks in data.items():
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

def decompose_path(path: str) -> dict:
    norm_path = file_helper.normalize_path(path)

    result = {
        'age':                  None,
        'mating date':          None,
        'testing date':         None,
        'group':                None,
        'technical repetition': None,
        'vial':                 None,
    }
    regex = re.compile(r'.*NGT-SCE/NGT_mating_\d+\.\d+\.\d+/(\d+)d(\d{8})_(\d{8})_NGT/.+/(\d+)_\d{8}_1\.(\d+)_start_v([1-5])\.avi$')

    m = regex.match(norm_path)
    if m is None:
        return None

    date_format = lambda date: f'{date[:2]}/{date[2:4]}/{date[4:]}'

    g = m.groups()
    result['age']                  = int(g[0])
    result['mating date']          = date_format(g[1])
    result['testing date']         = date_format(g[2])
    result['group']                = int(g[3])
    result['technical repetition'] = int(g[4])
    result['vial']                 = int(g[5])

    return result

def find_raw_data(video_path: str) -> str:
    """Find a path to the raw csv of a given video."""

    video_file   = file_helper.get_basename(video_path)
    video_folder = video_path.replace(video_file, '')

    video_file   = file_helper.get_basename_stem(video_path)
    raw_csv      = file_helper.join_paths(video_folder, f'{video_file}_raw.csv')

    return raw_csv if file_helper.check_existance(raw_csv) else None

