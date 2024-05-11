from FlyTracker import FlyTracker
import cv2, os
from tqdm import tqdm
import helper
import csv


def prepare_output_path(output_path):
    if not os.path.exists(output_path):
        os.makedirs(output_path)


def write_to_csv(data, output_path):
    with open(output_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['FRAME_NUMBER', 'ID', 'CONFIDENCE', 'X1', 'Y1', 'X2', 'Y2'])
        for frame_num, tracks in data.items():
            for track in tracks:
                writer.writerow([frame_num, *track])


def analyze_video(fly_tracker, video_path, output_path, draw_constraints = False):
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

    data = {}
    paths = {}

    while success:
        tracks = fly_tracker.detect(frame)

        data[progress_bar.n] = []

        for track in tracks:
            id, conf, x1, y1, x2, y2 = track
            center_x, center_y = helper.get_center(x1, y1, x2, y2)

            if id not in paths:
                paths[id] = []
            paths[id].append(helper.get_center(x1, y1, x2, y2))
            data[progress_bar.n].append(track)

            # if conf is None:  # lost target

            cv2.circle(
                img=        frame,
                center=     (center_x, center_y),
                radius=     5,
                color=      helper.rgb_to_bgr(helper.id_to_color(id)),
                thickness=  2
            )

        for _id, _points in paths.items():
            helper.draw_points_with_lines(
                image=      frame,
                points=     _points,
                color=      helper.rgb_to_bgr(helper.id_to_color(_id))
            )

        if draw_constraints:
            x1 = fly_tracker.constraints['x_min'] if fly_tracker.constraints['x_min'] is not None else 0
            x2 = fly_tracker.constraints['x_max'] if fly_tracker.constraints['x_max'] is not None else width - 1
            y1 = fly_tracker.constraints['y_min'] if fly_tracker.constraints['y_min'] is not None else 0
            y2 = fly_tracker.constraints['y_max'] if fly_tracker.constraints['y_max'] is not None else height - 1
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

    return data


if __name__ == '__main__':
    video_path = './model_evaluation/eval_short.avi'
    prepare_output_path('./model_tracking')

    _prefix = ''
    _suffix = '_result'

    ft = FlyTracker('./runs/detect/train7/weights/best.pt')
    ft.set_constraints(y_min=100)

    file_name = os.path.basename(os.path.normpath(video_path))
    output_path = f'./model_tracking/{_prefix}{file_name}{_suffix}'

    data = analyze_video(ft, video_path, f'{output_path}.mp4', draw_constraints=True)
    write_to_csv(data, f'{output_path}.csv')
    ft.reset_tracking()
    