import math
import numpy as np

def clamp(value, _min, _max):
    """
    Clamp a value between a minimum and maximum range.

    Args:
        value (float): The value to clamp.
        _min (float): The minimum allowable value.
        _max (float): The maximum allowable value.

    Returns:
        float: The clamped value.
    """
    return max(_min, min(value, _max))


def get_center(x1, y1, x2, y2):
    """
    Calculate the center point of a rectangle.

    Args:
        x1, y1 (float): Top-left corner coordinates.
        x2, y2 (float): Bottom-right corner coordinates.

    Returns:
        tuple[float, float]: The center coordinates (x, y).
    """
    return (x1 + x2) / 2, (y1 + y2) / 2


def get_ids(tracks):
    """
    Extract unique IDs from a list of tracks.

    Args:
        tracks (list): A list of track tuples where the first element is the ID.

    Returns:
        set: A set of unique IDs.
    """
    ids = set()
    for track in tracks:
        ids.add(track[0])
    return ids


def square_distance(p1, p2):
    """
    Calculate the Euclidean distance between two points.

    Args:
        p1, p2 (tuple[float, float]): Points as (x, y) coordinates.

    Returns:
        float: The distance between the two points.
    """
    x_dif = p2[0] - p1[0]
    y_dif = p2[1] - p1[1]
    return math.sqrt(math.pow(x_dif, 2) + math.pow(y_dif, 2))


def calculate_distances(point, tracks):
    """
    Calculate distances between a given point and tracks.

    Args:
        point (tuple[float, float]): The reference point as (x, y).
        tracks (list): A list of track tuples.

    Returns:
        list[tuple]: A list of tuples containing (id, confidence, distance).
    """
    results = []
    for track in tracks:
        id, conf, x1, y1, x2, y2 = track
        center = get_center(x1, y1, x2, y2)
        results.append((id, conf, square_distance(point, center)))
    return results


def find_nearest(results):
    """
    Find the nearest track based on distance.

    Args:
        results (list[tuple]): A list of tuples containing (id, confidence, distance).

    Returns:
        tuple: The tuple with the smallest distance.
    """
    min_index = 0
    for index in range(1, len(results)):
        min_index = index if results[index] < results[min_index] else min_index
    return results[min_index]


def generate_links(data, max_tracks_gap=3.0):
    """
    Generate links between swapped IDs based on proximity.

    Args:
        data (list[list]): Frames of tracks as a list of track lists.
        max_tracks_gap (float): Maximum allowable distance for linking tracks.

    Returns:
        dict: A dictionary mapping swapped IDs to original IDs.
    """
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
    """
    Apply spatial constraints to tracks.

    Args:
        data (list[list]): Frames of tracks as a list of track lists.
        constraints (dict): A dictionary defining min/max bounds for x and y.

    Returns:
        dict: Filtered data with tracks within constraints.
    """
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

        result[frame_number] = trimmed_tracks.values()
    return result


def propagate_links(links):
    """
    Propagate links to collapse chains of swapped IDs.

    Args:
        links (dict): Dictionary of swapped-to-original ID mappings.

    Returns:
        dict: Collapsed dictionary of ID mappings.
    """
    collapsed = {}
    for swapped in links:
        current = swapped
        while current in links and current != links[current]:
            current = links[current]
        collapsed[swapped] = current
    return collapsed


def process_data(data, links):
    """
    Process tracks data to fix swapped IDs based on links.

    Args:
        data (dict): Tracks data organized by frame.
        links (dict): Dictionary of ID links.

    Returns:
        dict: Processed tracks data with fixed IDs.
    """
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
    """
    Filter tracks by specific IDs.

    Args:
        data (dict): Tracks data organized by frame.
        requested_ids (set): Set of IDs to retain.

    Returns:
        dict: Filtered tracks data.
    """
    if requested_ids:
        filtered_data = {}
        for frame_number, tracks in data.items():
            filtered_data[frame_number] = [
                track for track in tracks if track[0] in requested_ids
            ]
        return filtered_data
    return data


def find_gaps_in_data(data):
    """
    Identify gaps in data for each ID.

    Args:
        data (dict): Tracks data organized by frame.

    Returns:
        list: A list of gaps per ID.
    """
    # track = tuple( id, conf, x1, y1, x2, y2 )
    # data  = dict{ frame_number: [track_1, track_2, ..., track_n] }
    appearances = {}
    # iterate over the data, and find for each id in which frames it appears
    for frame_number, tracks in data.items():
        for id in [t[0] for t in tracks]:
            appearances.setdefault(id, []).append(frame_number)

    gaps = []
    # iterate over the missing frames per id, and group them into gaps
    for id, frames in appearances.items():
        # find for each id in which frames it does not appear
        missing_frames = [f for f in range(frames[0], frames[-1] + 1) if f not in frames]
        if missing_frames:
            groups = [[missing_frames[0]]]
            for i in range(1, len(missing_frames)):
                if missing_frames[i] == missing_frames[i - 1] + 1:
                    groups[-1].append(missing_frames[i])
                else:
                    groups.append([missing_frames[i]])
            gaps.append((id, groups))

    return gaps


def fill_gaps_in_data(data, data_gaps):
    """
    Fill gaps in data by interpolating missing tracks.

    Args:
        data (dict): Tracks data organized by frame.
        data_gaps (list): A list of gaps to fill.

    Returns:
        dict: Data with filled gaps.
    """
    # track = tuple( id, conf, x1, y1, x2, y2 )
    # data  = dict{ frame_number: [track_1, track_2, ..., track_n] }
    
    def get_point(tracks, id):
        for track in tracks:
            tid, conf, x1, y1, x2, y2 = track
            if tid == id:
                return int((x1 + x2) / 2), int((y1 + y2) / 2)

    # iterate over the gaps of each id
    for id, gaps in data_gaps:
        for gap in gaps:
            # generate points on a straight line
            start_point = get_point(data[gap[0]-1], id)
            end_point   = get_point(data[gap[-1]+1], id)
            estimated = generate_points_between(start_point, end_point, len(gap))
            # insert the estimated points as track elements
            for i, frame in enumerate(gap):
                x, y = estimated[i]
                tracks = list(data[frame])
                tracks.append((id, None, x, y, x, y))
                data[frame] = sorted(tracks, key=lambda x: x[0])

    # return data without gaps
    return data


def generate_points_between(start, end, count):
    """
    Generate points on a straight line between two points.

    Args:
        start (tuple[int, int]): Starting point (x, y).
        end (tuple[int, int]): Ending point (x, y).
        count (int): Number of intermediate points to generate.

    Returns:
        list[tuple[int, int]]: List of generated points.
    """
    x_values = np.linspace(start[0], end[0], count + 2)
    y_values = np.linspace(start[1], end[1], count + 2)
    points = [(int(x), int(y)) for x, y in zip(x_values, y_values)]
    return points[1:-1]
