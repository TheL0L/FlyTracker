from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import cv2
import helper
from tqdm import tqdm

def conf_color(conf):
    value = 0 if conf is None else max(0, min(1, conf))
    red = int((1 - value) * 255)
    green = int(value * 255)
    return (red, green, 0)

def id_to_color(id):
    colors = {
        0: (255, 20, 147),    # Deep Pink
        1: (255, 0, 0),       # Red
        2: (0, 255, 0),       # Green
        3: (0, 0, 255),       # Blue
        4: (255, 255, 0),     # Yellow
        5: (255, 0, 255),     # Magenta
        6: (0, 255, 255),     # Cyan
        7: (128, 0, 0),       # Maroon
        8: (0, 128, 0),       # Green (dark)
        9: (0, 0, 128),       # Navy
        10: (128, 128, 0),    # Olive
        11: (128, 0, 128),    # Purple
        12: (0, 128, 128),    # Teal
        13: (128, 128, 128),  # Gray
        14: (192, 192, 192),  # Silver
        15: (255, 165, 0),    # Orange
        16: (255, 192, 203),  # Pink
        17: (255, 99, 71),    # Tomato
        18: (210, 105, 30),   # Chocolate
        19: (0, 255, 127),    # Spring Green
    }
    if id not in colors:
        return (255, 255, 255)
    return colors[id]

def reformat(result):
    x1, y1, x2, y2, score, class_id = result
    return [x1, y1, x2-x1, y2-y1], score, class_id

def rgb_to_bgr(color):
    r, g, b = color
    return b, g, r


object_tracker = DeepSort(max_age=10)
model = YOLO(helper.find_last_best_model_path())


video_path = './model_evaluation/eval_video.avi'
result_path = f'./model_tracking/result_test123.mp4'


# setup opencv video reader
stream = cv2.VideoCapture(video_path)
success, frame = stream.read()
height, width, _ = frame.shape
# writer = cv2.VideoWriter(
#     result_path,
#     cv2.VideoWriter_fourcc(*'mp4v'),
#     int(stream.get(cv2.CAP_PROP_FPS)),
#     (width, height)
# )

# frames_count = int(stream.get(cv2.CAP_PROP_FRAME_COUNT))
# progress_bar = tqdm(total=frames_count, desc='Annotation Progress', unit='frame')

cv2.namedWindow('Video', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Video', 2*width, 2*height)
CONF = 0.2
# read video file
while success:
    results = model(frame, verbose=False)[0]

    # for r in results.boxes.data.tolist():
    #     x1, y1, x2, y2, score, class_id = r
    #     cv2.circle(
    #         img=        frame,
    #         center=     helper.get_center(x1, y1, x2, y2),
    #         radius=     5,
    #         color=      rgb_to_bgr((255, 255, 255)),
    #         thickness=  2
    #     )

    detections = [reformat(result) for result in results.boxes.data.tolist()]
    detections = [d for d in detections if d[1] >= CONF]

    tracks = object_tracker.update_tracks(raw_detections=detections, frame=frame)

    for track in tracks:
        if not track.is_confirmed():
            continue

        track_id = int(track.track_id)
        score = track.get_det_conf()

        x1, y1, w, h = track.to_ltwh()
        x2, y2 = x1+w, y1+h

        cv2.circle(
            img=        frame,
            center=     helper.get_center(x1, y1, x2, y2),
            radius=     5,
            color=      rgb_to_bgr(conf_color(score)),
            thickness=  2
        )
        # cv2.putText(
        #     img=        frame,
        #     text=       f'{track_id}',
        #     org=        helper.make_point(x1, y1 - 3),
        #     fontFace=   cv2.FONT_HERSHEY_SIMPLEX,
        #     fontScale=  0.35,
        #     color=      id_to_color(track.track_id),
        #     thickness=  1,
        #     lineType=   cv2.LINE_AA
        # )
    
    cv2.imshow('Video', frame)
    cv2.waitKey(10)

    # writer.write(frame)
    # progress_bar.update()
    success, frame = stream.read()

# progress_bar.close()
stream.release()
# writer.release()
cv2.destroyAllWindows()
