from FlyTracker import FlyTracker
import cv2
from tqdm import tqdm
from data_postprocess import process_data, generate_links
from video_postprocess import annotate_video
import video_preprocess
import file_helper
import storage_helper


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
            id, conf, x1, y1, x2, y2 = track
            rounded_track = id, conf, round(x1), round(y1), round(x2), round(y2)
            data[progress_bar.n].append(rounded_track)

        progress_bar.update()
        success, frame = stream.read()
    
    # close streams and progress bars
    progress_bar.close()
    stream.release()

    return data


def process_video(ft: FlyTracker, video_path: str, output_root_path: str, prefix: str, suffix: str, preprocess_method) -> None:
    # prepare output basename
    file_name = file_helper.get_basename_stem(video_path)
    file_name = f'{prefix}{file_name}{suffix}'
    output_path = file_helper.join_paths(output_root_path, file_name)

    # read and process data
    raw_data = analyze_video(ft, video_path, preprocess_method)
    links = generate_links(raw_data, max_tracks_gap=3)
    processed_data = process_data(raw_data, links)

    # outputs
    storage_helper.write_to_csv(raw_data, f'{output_path}_raw.csv')
    annotate_video(processed_data, video_path, f'{output_path}.mp4', ft.constraints, True)
    storage_helper.write_to_csv(processed_data, f'{output_path}.csv')

    # notify the user
    print(f'results saved at:\n\t{output_path}.mp4\n\t{output_path}.csv\n')

    # reset tracking for next video
    ft.reset_tracking()
    return



if __name__ == '__main__':
    video_paths = [
        './showcase/4_short.avi',
    ]
    output_root_path = file_helper.normalize_path('./showcase/result')
    file_helper.prepare_output_path(output_root_path)

    prefix = ''
    suffix = '_result'

    # setup model
    ft = FlyTracker('./runs/detect/train7/weights/best.pt')
    ft.set_constraints(y_min=100)

    # define a preprocess method for the videos
    preprocess_method = None

    # iterate over videos
    for video_path in video_paths:
        # check video existance
        video_path = file_helper.normalize_path(video_path)
        if file_helper.check_existance(video_path):
            print(f'working on "{video_path}"...')
        else:
            print(f'could not locate the video at "{video_path}".')
            continue
        
        process_video(ft, video_path, output_root_path, prefix, suffix, preprocess_method)
        
    
