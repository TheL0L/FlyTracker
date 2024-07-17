from FlyTracker import FlyTracker
import cv2
from tqdm import tqdm
from data_postprocess import process_data, generate_links
from video_postprocess import annotate_video
import video_preprocess
import file_helper
import storage_helper
import sys, os, time


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


def analyze_video(fly_tracker: FlyTracker, video_path: str, start_frame, end_frame, frame_preprocess_method = None):
    # setup opencv video reader
    stream = cv2.VideoCapture(video_path)

    if start_frame is None:
        start_frame = 0
    if end_frame is None:
        end_frame = int(stream.get(cv2.CAP_PROP_FRAME_COUNT))
    
    stream.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    success, frame = stream.read()

    # prepare variable for storing data
    frames_count = int(stream.get(cv2.CAP_PROP_FRAME_COUNT))
    skipped_frames = list(range(start_frame)) + list(range(end_frame, frames_count))
    data = { k:[] for k in skipped_frames }

    # prepare preprocess method
    if frame_preprocess_method is None:
        frame_preprocess_method = lambda f: f

    # setup progress bar
    frames_count = end_frame - start_frame
    progress_bar = tqdm(total=frames_count, desc='Analysis Progress', unit='frame')

    frame_number = start_frame

    # iterate over video frames, and append tracks to the data variable
    while success and frame_number < end_frame:
        frame = frame_preprocess_method(frame)
        tracks = fly_tracker.detect(frame)

        data[frame_number] = []

        for track in tracks:
            data[frame_number].append(track)

        frame_number += 1
        progress_bar.update()
        success, frame = stream.read()
    
    # close streams and progress bars
    progress_bar.close()
    stream.release()

    return data


def process_video(ft: FlyTracker, video_path: str, start_frame, end_frame, preprocess_method) -> None:
    # prepare output basename
    output_path = storage_helper.get_prepared_path(video_path)

    # read and process data
    raw_data = analyze_video(ft, video_path, start_frame, end_frame, preprocess_method)
    links = generate_links(raw_data, max_tracks_gap=3)
    processed_data = process_data(raw_data, links)

    # outputs
    storage_helper.write_to_csv(raw_data, f'{output_path}_raw.csv')
    annotate_video(processed_data, video_path, f'{output_path}_result.mp4')
    storage_helper.write_to_csv(processed_data, f'{output_path}_result.csv')

    # notify the user
    print(f'results saved at:\n\t{output_path}_result.mp4\n\t{output_path}_result.csv\n\t{output_path}_raw.csv\n')

    # reset tracking for next video
    ft.reset_tracking()
    return


def break_down_args(args):
    def is_int(string: str) -> bool:
        try:
            int(string)
            return True
        except:
            return False
    
    # split into lists
    result = []
    for arg in args:
        if is_int(arg):
            result[-1].append(int(arg))
        else:
            result.append([arg])
    
    # format into tuples
    filtered_args = []
    for arg in result:
        if   len(arg) == 1:
            filtered_args.append((arg[0], None, None))
        elif len(arg) == 2:
            filtered_args.append((arg[0], arg[1], None))
        elif len(arg) == 3:
            filtered_args.append((arg[0], arg[1], arg[2]))

    # verify correctness
    for arg in filtered_args:
        path, start, end = arg
        if not isinstance(path, str):
            raise Exception()
        if not isinstance(start, int) and start is not None:
            raise Exception()
        if not isinstance(end, int) and end is not None:
            raise Exception()

    return filtered_args


def main():
    # sys.argv[0] is the name of the script
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
    # sys.argv[1:] contains the arguments passed to the script
    args = sys.argv[1:]
    if args:
        print(f'Arguments received: {args}\n')
        try:
            filtered_args = break_down_args(args)
        except:
            print('Could not parse the arguments, make sure they are formatted correctly!')
            raise Exception('Could not parse the arguments, make sure they are formatted correctly!')
    else:
        print('No arguments provided!')
        raise Exception('No arguments provided!')

    # setup model
    ft = FlyTracker('./_internal/weights.pt')

    # define a preprocess method for the videos
    preprocess_method = None

    # iterate over videos
    for arg in filtered_args:
        # check video existance
        video_path = file_helper.normalize_path(arg[0])
        start_frame = arg[1]
        end_frame = arg[2]
        if file_helper.check_existance(video_path):
            print(f'working on "{video_path}"...')
        else:
            print(f'could not locate the video at "{video_path}".')
            continue
        
        process_video(ft, video_path, start_frame, end_frame, preprocess_method)


if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except Exception as err:
        log_datetime = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
        file_helper.prepare_output_path('./logs/')

        with open(f'./logs/{log_datetime}.log', 'w') as logger:
            logger.write(f'Arguments: {sys.argv}\n\n')
            logger.write(f'{err}\n')
        sys.exit(1)
    
