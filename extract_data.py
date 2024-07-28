import file_helper
import csv
import re

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

