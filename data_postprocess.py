import math
import numpy as np

def clamp(value, _min, _max):
    return max(_min, min(value, _max))


def get_center(x1, y1, x2, y2):
    return (x1 + x2)/2, (y1 + y2)/2


def get_ids(tracks):
    ids = set()
    for track in tracks:
        ids.add(track[0])
    return ids


def square_distance(p1, p2):
    x_dif = p2[0] - p1[0]
    y_dif = p2[1] - p1[1]
    return math.sqrt( math.pow(x_dif, 2) + math.pow(y_dif, 2) )


def calculate_distances(point, tracks):
    results = []
    for track in tracks:
        id, conf, x1, y1, x2, y2 = track
        center = get_center(x1, y1, x2, y2)
        results.append((id, conf, square_distance(point, center)))
    return results


def find_nearest(results):
    min_index = 0
    for index in range(1, len(results)):
        min_index = index if results[index] < results[min_index] else min_index
    return results[min_index]


def generate_links(data, max_tracks_gap = 3.0):
    # prepare a dictionary for linking swapped IDs
    links = {}  # {swapped: original}

    # iterate over the data, in search for tracks that might be combined due to gaining new IDs
    last_frame_tracks = data[0]
    for frame_number in range(1, len(data)):
        # pull current frame tracks
        tracks = data[frame_number]
        
        # skip if last frame had no tracks
        if len(last_frame_tracks) == 0:
            last_frame_tracks = tracks      # update last_tracks to current_tracks
            continue
        
        # skip if current frame has no new IDs
        # use the fact that old IDs need 'FlyTracker.track_max_age' frames to be discarded
        old_ids = get_ids(last_frame_tracks)
        cur_ids = get_ids(tracks)
        if len(cur_ids.difference(old_ids)) == 0:
            last_frame_tracks = tracks      # update last_tracks to current_tracks
            continue

        # iterate over tracks, in search for new IDs
        for track in tracks:
            if track[0] in old_ids:
                continue
            # found a new ID, unpack track variables
            id, conf, x1, y1, x2, y2 = track
            center = get_center(x1, y1, x2, y2)

            # calculate distances between old_tracks and current_track
            candidates = calculate_distances(center, last_frame_tracks)
            # filter out candidates that have any detection confidence
            candidates = list(filter(lambda candidate: candidate[1] is None, candidates))

            if len(candidates) == 0:
                continue

            # find the nearest candidate
            nearest_id, _, dst = find_nearest(candidates)

            if dst > max_tracks_gap:
                continue

            # create a link between the current ID and the old_ID
            links[id] = nearest_id
        # update last_tracks to current_tracks
        last_frame_tracks = tracks
    return links


def apply_constraints(data, constraints):
    result = {}

    for frame_number in range(0, len(data)):
        tracks = data[frame_number]

        trimmed_tracks = {}
        for track in tracks:
            id, conf, x1, y1, x2, y2 = track
            if (not (constraints['x_min'] <= x1 <= constraints['x_max']) or
                not (constraints['x_min'] <= x2 <= constraints['x_max']) or
                not (constraints['y_min'] <= y1 <= constraints['y_max']) or
                not (constraints['y_min'] <= y2 <= constraints['y_max'])):
                continue
            trimmed_tracks[id] = (id, conf, x1, y1, x2, y2)

        # append processed frame to results
        result[frame_number] = trimmed_tracks.values()
    return result


def propagate_links(links):
    # links = {swapped: original}
    collapsed = {}
    for swapped in links:
        current = swapped
        while current in links and current != links[current]:
            current = links[current]
        collapsed[swapped] = current
    return collapsed


def process_data(data, links):
    # track = tuple( id, conf, x1, y1, x2, y2 )
    # data  = dict{ frame_number: [track_1, track_2, ..., track_n] }

    # collapse chains in the links
    links = propagate_links(links)

    # prepare variable for storing the processed data
    result = {}

    # iterate over the data, replacing swapped IDs
    for frame_number in range(0, len(data)):
        # pull current frame tracks
        tracks = data[frame_number]

        # override tracks based on generated links
        fixed_tracks = {}
        for track in tracks:
            id, conf, x1, y1, x2, y2 = track
            if id in links.keys():
                id = links[id]
            if id == 0:
                continue
            fixed_tracks[id] = (id, conf, x1, y1, x2, y2)

        # append processed frame to results
        result[frame_number] = fixed_tracks.values()
    return result


def filter_by_ids(data: dict, requested_ids: set) -> dict:
    # filter the data by the requested ids
    if requested_ids is not None and len(requested_ids) > 0:
        filtered_data = {}
        for frame_number, tracks in data.items():
            filtered_data[frame_number] = []
            for track in tracks:
                id, conf, x1, y1, x2, y2 = track
                if id not in requested_ids:
                    continue
                filtered_data[frame_number].append(track)
        data = filtered_data
    return data


def generate_points_between(start, end, count):
    # generate <count> (equally spaced) points on a straight line <start, end>
    x_values = np.linspace(start[0], end[0], count+2)
    y_values = np.linspace(start[1], end[1], count+2)
    points = [(int(x), int(y)) for x, y in zip(x_values, y_values)]
    return points[1:-1]