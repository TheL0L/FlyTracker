import cv2
from tqdm import tqdm

ROOT_PATH = './model_evaluation/'

# Load the videos
names = ['result_3.mp4', 'result_4.mp4', 'result_5.mp4', 'result_6.mp4', 'result_7.mp4']
captures, count = [], len(names)
for i in range(count):
    path = ROOT_PATH + names[i]
    captures.append(cv2.VideoCapture(path))


# Get the properties of the videos (frame width, frame height, etc.)
frame_width = int(captures[0].get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(captures[0].get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(captures[0].get(cv2.CAP_PROP_FPS))
total_frames = int(captures[0].get(cv2.CAP_PROP_FRAME_COUNT))

# Create an output video writer
out = cv2.VideoWriter(ROOT_PATH + '_merged.mp4', cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width * count, frame_height))

progress_bar = tqdm(total=total_frames, desc='Merging Progress', unit='frame')

# Iterate through the frames
for i in range(total_frames):
    rets, frames = [], []
    for j in range(count):
        ret, frame = captures[j].read()
        rets.append(ret)
        frames.append(frame)
    
    # Break the loop when the videos end
    if not all(rets):
        break

    # Resize the frames to fit side by side
    for j in range(count):
        frames[j] = cv2.resize(frames[j], (int(frame_width), int(frame_height)))

    # Merge frames side by side
    merged_frame = cv2.hconcat(frames)

    # Write the merged frame to the output video
    out.write(merged_frame)
    progress_bar.update()
    # # Display the frame (optional)
    # cv2.imshow('Merged Frame', merged_frame)
    # if cv2.waitKey(1) & 0xFF == ord('q'):
    #     break

progress_bar.close()
# Release the video objects and close the output video writer
for i in range(count):
    captures[i].release()
out.release()

# Close all OpenCV windows
cv2.destroyAllWindows()
