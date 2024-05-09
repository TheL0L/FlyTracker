from ultralytics import YOLO
import cv2
import helper
from tqdm import tqdm

model = YOLO(helper.find_last_best_model_path())

#video_path = './model_evaluation/eval_video.avi'
video_path = './model_evaluation/eval_short.avi'
#video_path = './model_evaluation/eval_multiple2.avi'

result_path = f'./model_evaluation/result_{helper.find_last_train()}.mp4'


# setup opencv video reader
video_capture = cv2.VideoCapture(video_path)
success, frame = video_capture.read()
height, width, _ = frame.shape
video_writer = cv2.VideoWriter(
    result_path,
    cv2.VideoWriter_fourcc(*'mp4v'),
    int(video_capture.get(cv2.CAP_PROP_FPS)),
    (width, height)
)

#dots = []
frames_count = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
progress_bar = tqdm(total=frames_count, desc='Annotation Progress', unit='frame')

# read video file
while success:
    results = model(frame, verbose=False)[0]

    for result in results.boxes.data.tolist():
        x1, y1, x2, y2, score, class_id = result

        # if confident enough in the result, annotate it
        if score > 0.2:
            #dots.append(helper.get_center(x1, y1, x2, y2))
            cv2.circle(
                img=        frame,
                center=     helper.get_center(x1, y1, x2, y2),
                radius=     5,
                color=      (0, 0, 255),
                thickness=  2
            )

            # cv2.rectangle(
            #     img=        frame,
            #     pt1=        helper.make_point(x1, y1),
            #     pt2=        helper.make_point(x2, y2),
            #     color=      (0, 255, 0),
            #     thickness=  1
            # )

            # cv2.putText(
            #     img=        frame,
            #     text=       f'{score:.3}',
            #     org=        helper.make_point(x1, y1 - 3),
            #     fontFace=   cv2.FONT_HERSHEY_SIMPLEX,
            #     fontScale=  0.35,
            #     color=      (0, 255, 0),
            #     thickness=  1,
            #     lineType=   cv2.LINE_AA
            # )
        
        # draw dots, hopefully it will resemble a path at the end
        # helper.draw_points_with_lines(frame, dots)

    video_writer.write(frame)
    progress_bar.update()
    success, frame = video_capture.read()

progress_bar.close()
video_capture.release()
video_writer.release()
cv2.destroyAllWindows()
