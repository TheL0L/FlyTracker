import helper
import cv2
from tqdm import tqdm
import numpy as np

def copy_frame(frame):
    return np.copy(frame)

def construct_paths(data, frame_number, paths = None):
    # prepare paths variable
    updated_paths = {} if paths is None else paths
    # construct paths from data
    for f in range(frame_number+1):
        for track in data[f]:
            id, conf, x1, y1, x2, y2 = track
            if id not in updated_paths:
                updated_paths[id] = []
            updated_paths[id].append(helper.get_center(x1, y1, x2, y2))
    return updated_paths

def draw_paths_onto_frame(frame_data, frame, paths = None):
    # annotate active paths with corresponding IDs
    for track in frame_data:
        id, conf, x1, y1, x2, y2 = track
        cv2.putText(
            img=        frame,
            text=       f'{id}',
            org=        helper.make_point(*helper.get_center(x1,y1,x2,y2)),
            fontFace=   cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=  0.4,
            color=      helper.rgb_to_bgr(helper.id_to_color(id)),
            thickness=  1,
            lineType=   cv2.LINE_AA
        )

    # draw paths constructed from points
    for _id, _points in paths.items():
        helper.draw_points_with_lines(
            image=      frame,
            points=     _points,
            color=      helper.rgb_to_bgr(helper.id_to_color(_id))
        )

def draw_constraints_onto_frame(frame, constraints):
    # get frame shape
    width, height, _ = frame.shape
    # draw constraints rectangle
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
        # get current frame number
        frame_number = progress_bar.n

        construct_paths(data, frame_number, paths)

        # draw a frame counter
        cv2.putText(
            img=        frame,
            text=       f'{frame_number}',
            org=        (1, 15),
            fontFace=   cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=  0.4,
            color=      helper.rgb_to_bgr((255, 0, 0)),
            thickness=  1,
            lineType=   cv2.LINE_AA
        )

        draw_paths_onto_frame(data[frame_number], frame, paths)
        
        if draw_constraints == True:
            draw_constraints_onto_frame(frame, constraints)

        writer.write(frame)

        progress_bar.update()
        success, frame = stream.read()
    
    progress_bar.close()
    stream.release()
    writer.release()
