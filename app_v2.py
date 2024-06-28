from FlyTracker import FlyTracker
import cv2, csv
from tqdm import tqdm
import helper
from data_postprocess import process_data
import video_preprocess
import file_helper


def preprocess_frame(frame):
    # RED LUT
    __R_LUT_X=[0, 100, 110, 150, 255]
    __R_LUT_Y=[0, 146, 238, 255, 255]

    # GREEN LUT
    __G_LUT_X=[0, 100, 110, 150, 255]
    __G_LUT_Y=[0, 0, 156, 255, 255]

    # BLUE LUT
    __B_LUT_X=[0, 63, 127, 191, 255]
    __B_LUT_Y=[0, 0, 255, 255, 255]
    lut_r = video_preprocess.create_lut_8uc1(__R_LUT_X, __R_LUT_Y)
    lut_g = video_preprocess.create_lut_8uc1(__G_LUT_X, __G_LUT_Y)
    lut_b = video_preprocess.create_lut_8uc1(__B_LUT_X, __B_LUT_Y)

    adjusted_frame = video_preprocess.apply_curves_to_channels(frame, lut_r, lut_g, lut_b)
    adjusted_frame = video_preprocess.to_grayscale_3c(adjusted_frame)
    return adjusted_frame


def analyze_video(fly_tracker, video_path, frame_preprocess_method = None):
    # setup opencv video reader
    stream = cv2.VideoCapture(video_path)
    success, frame = stream.read()

    # prepare variable for storing data
    data = {}

    # prepare preprocess method
    if frame_preprocess_method is None:
        frame_preprocess_method = lambda f: f

    # setup progress bar
    frames_count = int(stream.get(cv2.CAP_PROP_FRAME_COUNT))
    progress_bar = tqdm(total=frames_count, desc='Analysis Progress', unit='frame')

    # iterate over video frames, and append tracks to the data variable
    while success:
        frame = frame_preprocess_method(frame)
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



if __name__ == '__main__':
    video_paths = [
        './showcase/4_short.avi',
    ]
    output_root_path = file_helper.normalize_path('./showcase/result')
    file_helper.prepare_output_path(output_root_path)

    _prefix = ''
    _suffix = '_result'

    # setup model
    ft = FlyTracker('./runs/detect/train7/weights/best.pt')
    ft.set_constraints(y_min=100)

    # define a preprocess method for the videos
    _preprocess_method = None

    # iterate over videos
    for video_path in video_paths:
        # check video existance
        video_path = file_helper.normalize_path(video_path)
        if file_helper.check_existance(video_path):
            print(f'working on {video_path}...')
        else:
            print(f'could not locate the video at "{video_path}".')
            continue

        # prepare output basename
        file_name = file_helper.get_basename_stem(video_path)
        file_name = f'{_prefix}{file_name}{_suffix}'
        output_path = file_helper.join_paths(output_root_path, file_name)

        # read and process data
        raw_data = analyze_video(ft, video_path, _preprocess_method)
        processed_data = process_data(raw_data, max_tracks_gap=3)

        # outputs
        annotate_video(processed_data, video_path, f'{output_path}.mp4', ft.constraints, True)
        write_to_csv(processed_data, f'{output_path}.csv')

        # notify the user
        print(f'results saved at:\n\t{output_path}.mp4\n\t{output_path}.csv\n')

        # reset tracking for next video
        ft.reset_tracking()
    
