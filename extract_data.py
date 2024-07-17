import file_helper
import csv
import re

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

