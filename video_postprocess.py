import cv2
import numpy as np

def id_to_color(id):
    """
    Maps an ID to a specific color.

    Parameters:
    id (int): The ID to be mapped to a color.

    Returns:
    tuple: A tuple representing the color in BGR format.
    """
    colors = {
        0:  ( 0  ,  0  ,  255 ),     # Red
        1:  ( 255,  0  ,  0   ),     # Blue
        2:  ( 0  ,  255,  0   ),     # Green
        3:  ( 0  ,  165,  255 ),     # Orange
        4:  ( 130,  0  ,  75  ),     # Indigo
        5:  ( 147,  20 ,  255 ),     # Deep Pink
        6:  ( 255,  255,  0   ),     # Cyan
        7:  ( 128,  0  ,  128 ),     # Purple
        8:  ( 0  ,  255,  255 ),     # Yellow
        9:  ( 128,  128,  0   ),     # Teal
        10: ( 255,  0  ,  255 ),     # Magenta
        11: ( 0  ,  100,  0   ),     # Dark Green
        12: ( 0  ,  69 ,  255 ),     # Orange Red
        13: ( 79 ,  79 ,  47  ),     # Dark Slate Gray
        14: ( 0  ,  0  ,  139 ),     # Dark Red
        15: ( 139,  0  ,  0   ),     # Dark Blue
        16: ( 60 ,  20 ,  220 ),     # Crimson
        17: ( 130,  0  ,  75  ),     # Indigo
        18: ( 50 ,  205,  154 ),     # Yellow Green
        19: ( 0  ,  128,  128 )      # Olive
    }
    return colors[id % len(colors)]

def copy_frame(frame):
    """
    Creates a copy of the frame.

    Parameters:
    frame (numpy.ndarray): The frame to be copied.

    Returns:
    numpy.ndarray: The copied frame.
    """
    return np.copy(frame)

def construct_paths(data, end_frame, paths = None, start_frame = None):
    """
    Constructs and updates paths for tracked objects over a sequence of frames.

    Parameters:
    data (dict): A dictionary where keys are frame numbers and values are lists of tracks.
    end_frame (int): The ending frame number up to which paths are constructed.
    paths (dict, optional): A dictionary to store the paths of tracked objects.
                            Keys are object IDs and values are lists of (x, y) tuples representing the center of the bounding box.
                            Defaults to None, in which case a new dictionary is created.
    start_frame (int, optional): The starting frame number from which paths are constructed.
                                 Defaults to the value of end_frame if not provided.

    Returns:
    dict: Updated paths of tracked objects, where keys are object IDs and values are lists of (x, y) tuples.
    """
    # prepare variables
    updated_paths = {} if paths is None else paths
    start_frame = end_frame if start_frame is None else start_frame
    # construct paths from data
    for f in range(start_frame, end_frame+1):
        for track in data[f]:
            id, conf, x1, y1, x2, y2 = track
            if id not in updated_paths:
                updated_paths[id] = []
            updated_paths[id].append(tuple(np.int32([(x1 + x2) / 2, (y1 + y2) / 2])))
    return updated_paths

def draw_paths_onto_frame(frame_data, frame, paths):
    """
    Draws the paths and annotations onto the frame.

    Parameters:
    frame_data (list): A list of tracks for the current frame.
    frame (numpy.ndarray): The frame onto which paths and annotations are drawn.
    paths (dict, optional): A dictionary containing the paths of tracked objects.
                            Keys are object IDs and values are lists of (x, y) tuples representing the path.
                            Defaults to None.
    """
    # annotate active paths with corresponding IDs
    for track in frame_data:
        id, conf, x1, y1, x2, y2 = track
        cv2.putText(
            img=        frame,
            text=       f'{id}',
            org=        tuple(np.int32([(x1 + x2) / 2, (y1 + y2) / 2])),
            fontFace=   cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=  0.4,
            color=      id_to_color(id),
            thickness=  1,
            lineType=   cv2.LINE_AA
        )

    # draw paths constructed from points
    for _id, _points in paths.items():
        cv2.polylines(
            img=        frame,
            pts=        [np.array(_points, dtype=np.int32).reshape((-1, 1, 2))],
            isClosed=   False,
            color=      id_to_color(_id),
            thickness=  1
        )

def draw_constraints_onto_frame(frame, constraints):
    """
    Draws constraints as a rectangle onto the frame.

    Parameters:
    frame (numpy.ndarray): The frame onto which constraints are drawn.
    constraints (dict): A dictionary containing the constraint values for x and y coordinates.
                        Keys are 'x_min', 'x_max', 'y_min', 'y_max'.
    """
    cv2.rectangle(
        img=        frame,
        pt1=        tuple(np.int32([constraints['x_min'], constraints['y_min']])),
        pt2=        tuple(np.int32([constraints['x_max'], constraints['y_max']])),
        color=      (0, 0, 255),
        thickness=  1
    )

def annotate_video(data, video_path, output_path, constraints = None, draw_constraints = False):
    """
    Annotates a video with paths and constraints.

    Parameters:
    data (dict): A dictionary where keys are frame numbers and values are lists of tracks.
    video_path (str): Path to the input video file.
    output_path (str): Path to the output annotated video file.
    constraints (dict, optional): A dictionary containing the constraint values for x and y coordinates.
                                  Keys are 'x_min', 'x_max', 'y_min', 'y_max'.
    draw_constraints (bool, optional): Whether to draw constraints on the video frames.
                                       Defaults to False.
    """
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

    # prepare a variable to hold the paths
    paths = {}

    frame_number = 0
    while success:
        construct_paths(data, frame_number, paths)

        # draw a frame counter
        cv2.putText(
            img=        frame,
            text=       f'{frame_number}',
            org=        (1, 15),
            fontFace=   cv2.FONT_HERSHEY_SIMPLEX,
            fontScale=  0.4,
            color=      (0, 0, 255),
            thickness=  1,
            lineType=   cv2.LINE_AA
        )

        draw_paths_onto_frame(data[frame_number], frame, paths)
        
        if draw_constraints == True:
            draw_constraints_onto_frame(frame, constraints)

        writer.write(frame)

        frame_number += 1
        success, frame = stream.read()
    
    stream.release()
    writer.release()
