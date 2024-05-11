from FlyTracker import FlyTracker
import cv2, csv, math, os
from tqdm import tqdm
import helper


def analyze_video(fly_tracker, video_path):
    # setup opencv video reader
    stream = cv2.VideoCapture(video_path)
    success, frame = stream.read()

    # prepare variable for storing data
    data = {}

    # setup progress bar
    frames_count = int(stream.get(cv2.CAP_PROP_FRAME_COUNT))
    progress_bar = tqdm(total=frames_count, desc='Analysis Progress', unit='frame')

    # iterate over video frames, and append tracks to the data variable
    while success:
        tracks = fly_tracker.detect(frame)

        data[progress_bar.n] = []

        for track in tracks:
            data[progress_bar.n].append(track)

        progress_bar.update()
        success, frame = stream.read()
    
    # close streams and progress bars
    progress_bar.close()
    stream.release()

    return data


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
        center = helper.get_center(x1, y1, x2, y2)
        results.append((id, conf, square_distance(point, center)))
    return results


def find_closest(results):
    min_index = 0
    for index in range(1, len(results)):
        min_index = index if results[index] < results[min_index] else min_index
    return results[min_index]


def get_index(id, tracks):
    for index in range(len(tracks)):
        if tracks[index][0] == id:
            return index
    return None


# TODO: Debug this
def process_data(data, max_tracks_gap = 3.0):
    # track = tuple( id, conf, x1, y1, x2, y2 )
    # data  = dict{ frame_number: [track_1, track_2, ..., track_n] }
    
    # prepare variable for storing the processed data
    result = {0: []}

    # prepare a dictionary for linking swapped IDs
    links = {}

    # setup progress bar
    progress_bar = tqdm(total=len(data), desc='Processing Progress', unit='frame')

    # iterate over the data, in search for tracks that might be combined due to gaining new IDs
    last_frame_tracks = data[0]
    progress_bar.update()
    for frame_number in range(1, len(data)):
        # pull current frame tracks
        tracks = data[frame_number]
        
        # skip if last frame had no tracks
        if len(last_frame_tracks) == 0:
            last_frame_tracks = tracks      # update last_tracks to current_tracks
            result[frame_number] = tracks   # append frame to results
            progress_bar.update()
            continue
        
        # skip if current frame has no new IDs
        # use the fact that old IDs need 'FlyTracker.track_max_age' frames to be discarded
        old_ids = get_ids(last_frame_tracks)
        cur_ids = get_ids(tracks)
        if len(cur_ids.difference(old_ids)) == 0:
            last_frame_tracks = tracks      # update last_tracks to current_tracks
            result[frame_number] = tracks   # append frame to results
            progress_bar.update()
            continue

        # iterate over tracks, in search for new IDs
        for track in tracks:
            if track[0] in old_ids:
                continue
            # found a new ID, unpack track variables
            id, conf, x1, y1, x2, y2 = track
            center = helper.get_center(x1, y1, x2, y2)

            # calculate distances between old_tracks and current_track
            candidates = calculate_distances(center, last_frame_tracks)
            # filter out candidates that have any detection confidence
            candidates = list(filter(lambda candidate: candidate[1] is None, candidates))

            if len(candidates) == 0:
                continue

            # find the closest candidate
            close_id, _, dst = find_closest(candidates)

            if dst > max_tracks_gap:
                continue

            # create a link between the current ID and the old_ID
            links[id] = close_id

        # override tracks based on generated links
        fixed_tracks = {}
        for track in tracks:
            id, conf, x1, y1, x2, y2 = track
            if id in links.keys():
                id = links[id]
            fixed_tracks[id] = (id, conf, x1, y1, x2, y2)

        last_frame_tracks = fixed_tracks.values()      # update last_tracks to current_tracks
        result[frame_number] = fixed_tracks.values()   # append processed frame to results
        progress_bar.update()

    progress_bar.close()
    return result


# TODO: think about the annotation workflow, a decorator approach would be great
def annotate_video(data, video_path, output_path, constraints, draw_constraints = False):
    # setup opencv video reader
    stream = cv2.VideoCapture(video_path)
    success, frame = stream.read()
    height, width, _ = frame.shape

    # setup opencv video writer
    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*'mp4v'),
        int(stream.get(cv2.CAP_PROP_FPS)),
        (width, height)
    )

    # setup progress bar
    frames_count = int(stream.get(cv2.CAP_PROP_FRAME_COUNT))
    progress_bar = tqdm(total=frames_count, desc='Annotation Progress', unit='frame')

    # prepare a variable to hold the paths
    paths = {}

    while success:
        # write a frame counter
        cv2.putText(
            img=        frame,
            text=       f'{progress_bar.n}',
            org=        (1, 15),
            fontFace=   cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=  0.4,
            color=      helper.rgb_to_bgr((255, 0, 0)),
            thickness=  1,
            lineType=   cv2.LINE_AA
        )

        # add current frame's points to the paths
        for track in data[progress_bar.n]:
            id, conf, x1, y1, x2, y2 = track
            if id not in paths:
                paths[id] = []
            paths[id].append(helper.get_center(x1, y1, x2, y2))

        # draw paths constructed from points
        for _id, _points in paths.items():
            helper.draw_points_with_lines(
                image=      frame,
                points=     _points,
                color=      helper.rgb_to_bgr(helper.id_to_color(_id))
            )
        
        # draw constraints rectangle
        if draw_constraints:
            x1 = constraints['x_min'] if constraints['x_min'] is not None else 0
            x2 = constraints['x_max'] if constraints['x_max'] is not None else width - 1
            y1 = constraints['y_min'] if constraints['y_min'] is not None else 0
            y2 = constraints['y_max'] if constraints['y_max'] is not None else height - 1
            cv2.rectangle(
                img=        frame,
                pt1=        helper.make_point(x1, y1),
                pt2=        helper.make_point(x2, y2),
                color=      (0, 0, 255),
                thickness=  1
            )

        writer.write(frame)

        progress_bar.update()
        success, frame = stream.read()
    
    progress_bar.close()
    stream.release()
    writer.release()


def write_to_csv(data, output_path):
    with open(output_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['FRAME_NUMBER', 'ID', 'CONFIDENCE', 'X1', 'Y1', 'X2', 'Y2'])
        for frame_num, tracks in data.items():
            for track in tracks:
                writer.writerow([frame_num, *track])


def prepare_output_path(output_path):
    if not os.path.exists(output_path):
        os.makedirs(output_path)


if __name__ == '__main__':
    video_path = './model_evaluation/eval_video.avi'
    prepare_output_path('./model_tracking')

    _prefix = ''
    _suffix = '_result_reworked'

    file_name = os.path.basename(os.path.normpath(video_path))
    output_path = f'./model_tracking/{_prefix}{file_name}{_suffix}'

    ft = FlyTracker('./runs/detect/train7/weights/best.pt')
    ft.set_constraints(y_min=100)

    raw_data = analyze_video(ft, video_path)

    # with open('./raw_data.data', 'r') as datafile:
    #     raw_data = datafile.read()
    #     raw_data = eval(raw_data)

    processed_data = process_data(raw_data, max_tracks_gap=10)

    annotate_video(processed_data, video_path, f'{output_path}.mp4', ft.constraints, True)
    write_to_csv(processed_data, f'{output_path}.csv')