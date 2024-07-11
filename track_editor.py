import tkinter as tk
from tkinter import ttk
from tkinter import font
from tkinter import simpledialog
import cv2, re
from PIL import Image, ImageTk
import storage_helper
import data_postprocess
import video_postprocess
import file_helper

__INPUT_VIDEO = './showcase/4_short.avi'
__OUTPUT_ROOT_PATH = file_helper.normalize_path('./showcase/result')

__PREFIX = ''
__SUFFIX = '_result'

__BACKGROUND_DARK  = '#1E1E1E'
__BACKGROUND_LIGHT = '#303030'


def deselect_all_entries(event):
    widget = event.widget
    if not isinstance(widget, tk.Entry):
        ROOT_WINDOW.focus()

def restart_preview():
    global VIDEO_CAPTURE, timeline_slider
    VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, 0)
    timeline_slider.set(VIDEO_CAPTURE.get(cv2.CAP_PROP_POS_FRAMES))

def resume_preview():
    global IS_PLAYING
    IS_PLAYING = True

def pause_preview():
    global IS_PLAYING
    IS_PLAYING = False

def read_zoom_from_controls():
    global ZOOM_SCALAR

    ZOOM_SCALAR = zoom_slider.get() / 100

def read_speed_from_controls():
    global PLAYBACK_DELAY_MS

    speed_factor = speed_slider.get() / 100
    PLAYBACK_DELAY_MS = int(1000 / (VIDEO_CAPTURE.get(cv2.CAP_PROP_FPS) * speed_factor))

def read_timeline_value():
    global VIDEO_CAPTURE, timeline_slider

    timeline_pos = int(timeline_slider.get())
    if timeline_pos != int(VIDEO_CAPTURE.get(cv2.CAP_PROP_POS_FRAMES) - 1):
        VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, timeline_pos)

def update_frame():
    global VIDEO_CAPTURE, preview_panel, merged_frame, timeline_slider

    read_timeline_value()

    if IS_PLAYING:
        ret, frame = VIDEO_CAPTURE.read()
        if not ret:
            VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, 0)  # restart video
            ret, frame = VIDEO_CAPTURE.read()
    else:
        VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, VIDEO_CAPTURE.get(cv2.CAP_PROP_POS_FRAMES) - 1)  # repeat last frame
        ret, frame = VIDEO_CAPTURE.read()
    
    # update timeline position
    frame_number = int(VIDEO_CAPTURE.get(cv2.CAP_PROP_POS_FRAMES) - 1)
    timeline_slider.set(frame_number)

    read_zoom_from_controls()
    read_speed_from_controls()

    fly_paths = video_postprocess.construct_paths(PROCESSED_DATA, frame_number, start_frame=0)
    adjusted_frame = video_postprocess.copy_frame(frame)
    video_postprocess.draw_paths_onto_frame(PROCESSED_DATA[frame_number], adjusted_frame, fly_paths)

    # place adjusted and original frames side by side
    height, width, _ = frame.shape
    if width < height:
        merged_frame = cv2.hconcat([adjusted_frame, frame])
    else:
        merged_frame = cv2.vconcat([adjusted_frame, frame])

    # Convert the frame to a format that can be used by tk
    img = Image.fromarray(cv2.cvtColor(merged_frame, cv2.COLOR_BGR2RGB))
    resized = img.resize((int(img.width * ZOOM_SCALAR), int(img.height * ZOOM_SCALAR)), Image.LANCZOS)
    imgtk = ImageTk.PhotoImage(image=resized)

    # Update the image in the panel
    preview_panel.imgtk = imgtk
    preview_panel.config(image=imgtk)
    
    # Call this function again after some delay
    ROOT_WINDOW.after(PLAYBACK_DELAY_MS, update_frame)

def auto_process():
    global PROCESSED_DATA, LINKS, gap_entry
    try:
        gap = int(gap_entry.get())
    except:
        pass
    LINKS = data_postprocess.generate_links(STORED_RAW_DATA, gap)
    populate_links()
    PROCESSED_DATA = data_postprocess.process_data(STORED_RAW_DATA, LINKS)

def populate_links():
    global links_listbox
    links_listbox.delete(0, tk.END)
    for swapped, actual in LINKS.items():
        links_listbox.insert(tk.END, f'{swapped:<5}->{actual:>5}')

def list_add():
    global LINKS, PROCESSED_DATA, links_listbox
    ans = simpledialog.askstring("Input", "Enter 2 IDs to merge:")
    if ans is None:
        return
    
    ids = [int(num) for num in re.findall(r'\d+', ans)]

    swapped, actual = max(ids), min(ids)
    LINKS[swapped] = actual
    populate_links()
    PROCESSED_DATA = data_postprocess.process_data(STORED_RAW_DATA, LINKS)

def list_edt():
    global LINKS, PROCESSED_DATA, links_listbox
    selected_index = links_listbox.curselection()
    if not selected_index:
        return
    
    current_value: str = links_listbox.get(selected_index)
    swapped, actual = current_value.replace('->', ' ').split(maxsplit=2)
    swapped, actual = int(swapped), int(actual)
    
    ans = simpledialog.askstring("Input", "Enter 2 IDs to merge:", initialvalue=f'{swapped} {actual}')
    if ans is None:
        return
    
    ids = [int(num) for num in re.findall(r'\d+', ans)]

    del LINKS[swapped]
    swapped, actual = max(ids), min(ids)
    LINKS[swapped] = actual
    populate_links()
    PROCESSED_DATA = data_postprocess.process_data(STORED_RAW_DATA, LINKS)

def list_del():
    global LINKS, PROCESSED_DATA, links_listbox
    selected_index = links_listbox.curselection()
    if not selected_index:
        return
    current_value: str = links_listbox.get(selected_index)
    swapped, actual = current_value.replace('->', ' ').split(maxsplit=2)
    del LINKS[int(swapped)]
    populate_links()
    PROCESSED_DATA = data_postprocess.process_data(STORED_RAW_DATA, LINKS)

def export_csv():
    video_file   = file_helper.get_basename(__INPUT_VIDEO)
    video_folder = __INPUT_VIDEO.replace(video_file, '')
    file_name = file_helper.get_basename_stem(__INPUT_VIDEO)
    output_path = file_helper.join_paths(video_folder, file_name)

    # outputs
    storage_helper.write_to_csv(PROCESSED_DATA, f'{output_path}_result.csv')

def export_mp4():
    import video_postprocess
    video_file   = file_helper.get_basename(__INPUT_VIDEO)
    video_folder = __INPUT_VIDEO.replace(video_file, '')
    file_name = file_helper.get_basename_stem(__INPUT_VIDEO)
    output_path = file_helper.join_paths(video_folder, file_name)

    # outputs  # TODO: save model constraints?
    video_postprocess.annotate_video(PROCESSED_DATA, __INPUT_VIDEO, f'{output_path}_result.mp4', None, False)

# read raw data from csv file
raw_file = storage_helper.find_raw_data(__INPUT_VIDEO)
LINKS = {}
PROCESSED_DATA = None
STORED_RAW_DATA = storage_helper.read_from_csv(raw_file) if raw_file is not None else None

# Initialize the video capture
VIDEO_CAPTURE = cv2.VideoCapture(__INPUT_VIDEO)
VIDEO_TOTAL_FRAMES = int(VIDEO_CAPTURE.get(cv2.CAP_PROP_FRAME_COUNT))
IS_PLAYING = True
ZOOM_SCALAR = 2.2
PLAYBACK_DELAY_MS = int(1000 / VIDEO_CAPTURE.get(cv2.CAP_PROP_FPS))

# Initialize tk window
ROOT_WINDOW = tk.Tk()
ROOT_WINDOW.title("Effect Preview")
ROOT_WINDOW.state('zoomed')

# Set the default font for all widgets
monospace_font = font.Font(family='Courier', size=12)
ROOT_WINDOW.option_add("*Font", monospace_font)


# Create the left and right frames
LEFT_FRAME = tk.Frame(ROOT_WINDOW, bg=__BACKGROUND_LIGHT)
LEFT_FRAME.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

RIGHT_FRAME = tk.Frame(ROOT_WINDOW, bg=__BACKGROUND_DARK)
RIGHT_FRAME.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Create controls frame for preview panel
PREVIEW_FRAME = tk.Frame(RIGHT_FRAME, bg=RIGHT_FRAME.cget('bg'))
PREVIEW_FRAME.pack(fill=tk.BOTH, expand=True)

# Add preview panel to the preview frame
preview_panel = tk.Label(PREVIEW_FRAME, bg=PREVIEW_FRAME.cget('bg'))
preview_panel.pack()

# Add preview timeline
timeline_slider = tk.Scale(PREVIEW_FRAME, from_=0, to=VIDEO_TOTAL_FRAMES, orient=tk.HORIZONTAL)
timeline_slider.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

# Create two vertically stacked control frames inside the right frame with a separator
PREVIEW_CONTROL_FRAME = tk.Frame(LEFT_FRAME, bg=LEFT_FRAME.cget('bg'))
PREVIEW_CONTROL_FRAME.pack(fill=tk.BOTH, expand=False, padx=20, pady=20)

CONTROL_SPACING_FRAME = tk.Frame(LEFT_FRAME, bg=__BACKGROUND_DARK, height=10)
CONTROL_SPACING_FRAME.pack(fill=tk.X, expand=False)

DATA_CONTROL_FRAME = tk.Frame(LEFT_FRAME, bg=LEFT_FRAME.cget('bg'))
DATA_CONTROL_FRAME.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

CONTROL_SPACING_FRAME = tk.Frame(LEFT_FRAME, bg=__BACKGROUND_DARK, height=10)
CONTROL_SPACING_FRAME.pack(fill=tk.X, expand=False)

EXPORT_FRAME = tk.Frame(LEFT_FRAME, bg=LEFT_FRAME.cget('bg'))
EXPORT_FRAME.pack(fill=tk.BOTH, expand=False, padx=20, pady=20)

# Add buttons to control preview
controls_label = ttk.Label(PREVIEW_CONTROL_FRAME, text='Preview controls:')
controls_label.grid(row=0, column=0, padx=5, pady=5)

play_preview_button = tk.Button(PREVIEW_CONTROL_FRAME, width=20, text="Play", command=resume_preview)
play_preview_button.grid(row=0, column=1, padx=5, pady=5)

pause_preview_button = tk.Button(PREVIEW_CONTROL_FRAME, width=20, text="Pause", command=pause_preview)
pause_preview_button.grid(row=0, column=2, padx=5, pady=5)

restart_preview_button = tk.Button(PREVIEW_CONTROL_FRAME, width=20, text="Restart", command=restart_preview)
restart_preview_button.grid(row=0, column=3, padx=5, pady=5)

# Add sliders to control preview
zoom_label = ttk.Label(PREVIEW_CONTROL_FRAME, text='Zoom level [%]:')
zoom_label.grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
zoom_slider = tk.Scale(PREVIEW_CONTROL_FRAME, from_=50, to=250, orient=tk.HORIZONTAL, length=300)
zoom_slider.set(ZOOM_SCALAR * 100)
zoom_slider.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

speed_label = ttk.Label(PREVIEW_CONTROL_FRAME, text='Playback speed [%]:')
speed_label.grid(row=1, column=2, sticky=tk.E, padx=5, pady=5)
speed_slider = tk.Scale(PREVIEW_CONTROL_FRAME, from_=10, to=200, orient=tk.HORIZONTAL, length=300)
speed_slider.set(100)
speed_slider.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)


# Add links control frame
LINKS_FRAME = tk.Frame(DATA_CONTROL_FRAME, bg=DATA_CONTROL_FRAME.cget('bg'))
LINKS_FRAME.grid(row=0, column=0, padx=10, pady=10)

links_label = tk.Label(LINKS_FRAME, text='Links:')
links_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)

links_listbox = tk.Listbox(LINKS_FRAME)
links_listbox.grid(row=1, column=0, columnspan=2, sticky=tk.EW)


gap_label = ttk.Label(LINKS_FRAME, text='Gap threshold [px]:')
gap_label.grid(row=2, column=0, sticky=tk.EW, padx=5, pady=5)
gap_entry = tk.Entry(LINKS_FRAME)
gap_entry.insert(0, '3')
gap_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

auto_button = tk.Button(LINKS_FRAME, text="Automatically find links", command=auto_process)
auto_button.grid(row=3, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)


LINK_BUTTONS_FRAME = tk.Frame(DATA_CONTROL_FRAME, bg=DATA_CONTROL_FRAME.cget('bg'))
LINK_BUTTONS_FRAME.grid(row=0, column=1)

list_add_button = tk.Button(LINK_BUTTONS_FRAME, text="Add link", command=list_add)
list_add_button.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=5)

list_edt_button = tk.Button(LINK_BUTTONS_FRAME, text="Edit link", command=list_edt)
list_edt_button.grid(row=1, column=0, sticky=tk.EW, padx=5, pady=5)

list_del_button = tk.Button(LINK_BUTTONS_FRAME, text="Remove link", command=list_del)
list_del_button.grid(row=2, column=0, sticky=tk.EW, padx=5, pady=5)


# Add export buttons
EXPORT_BUTTONS_FRAME = tk.Frame(EXPORT_FRAME, bg=EXPORT_FRAME.cget('bg'))
EXPORT_BUTTONS_FRAME.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)

export_cvs_button = tk.Button(EXPORT_BUTTONS_FRAME, text="Export to CSV", command=export_csv)
export_cvs_button.grid(row=0, column=0, sticky=tk.SE, padx=5, pady=5)

export_mp4_button = tk.Button(EXPORT_BUTTONS_FRAME, text="Export to MP4", command=export_mp4)
export_mp4_button.grid(row=0, column=1, sticky=tk.SE, padx=5, pady=5)



# Add event listeners
ROOT_WINDOW.bind("<Button-1>", deselect_all_entries)

auto_process()
# Start the frame update loop
update_frame()

# Start the tk event loop
ROOT_WINDOW.mainloop()

# Release the video capture object
VIDEO_CAPTURE.release()
