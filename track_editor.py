import tkinter as tk
from tkinter import ttk
from tkinter import font
from tkinter import messagebox, simpledialog, filedialog
import cv2, re
from PIL import Image, ImageTk
import storage_helper
import data_postprocess
import video_postprocess
import file_helper
import threading, time, subprocess

__INPUT_VIDEO = None
__MODEL_EXE   = './flytracker_app.exe'

__BACKGROUND_DARK  = '#1E1E1E'
__BACKGROUND_LIGHT = '#303030'

__AWAITING_VIDEO = True


def read_entry(entry: tk.Entry) -> int:
    try:
        return int(entry.get())
    except:
        return None

def write_entry(entry: tk.Entry, value: str):
    entry.delete(0, tk.END)
    entry.insert(0, value)

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

def read_path_length_from_controls():
    global PATH_LENGTH

    PATH_LENGTH = read_entry(path_length_entry)
    PATH_LENGTH = None if PATH_LENGTH is None or PATH_LENGTH < 0 else PATH_LENGTH

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

def await_file_opened():
    global STORED_RAW_DATA, VIDEO_CAPTURE, __AWAITING_VIDEO
    global VIDEO_TOTAL_FRAMES, IS_PLAYING, PLAYBACK_DELAY_MS, timeline_slider
    global margins_xmin_entry, margins_xmax_entry
    global margins_ymin_entry, margins_ymax_entry

    if __INPUT_VIDEO is not None:
        # read raw data from csv file
        raw_file = storage_helper.find_raw_data(__INPUT_VIDEO)
        STORED_RAW_DATA = storage_helper.read_from_csv(raw_file) if raw_file is not None else None

        if VIDEO_CAPTURE is None:
            # Initialize the video capture
            VIDEO_CAPTURE = cv2.VideoCapture(__INPUT_VIDEO)
            VIDEO_TOTAL_FRAMES = int(VIDEO_CAPTURE.get(cv2.CAP_PROP_FRAME_COUNT))
            PLAYBACK_DELAY_MS = int(1000 / VIDEO_CAPTURE.get(cv2.CAP_PROP_FPS))

        if STORED_RAW_DATA is not None:
            # Enable elements after a video has loaded
            toggle_all_widgets(RIGHT_FRAME, True)
            toggle_all_widgets(PREVIEW_CONTROL_FRAME, True)
            toggle_all_widgets(FT_CONTROL_FRAME, True)
            toggle_all_widgets(DATA_CONTROL_FRAME, True)
            toggle_all_widgets(EXPORT_BUTTONS_FRAME, True)

            # Adjust the timeline bounds 
            timeline_slider.config(to=VIDEO_TOTAL_FRAMES)

            # set default margins for the constraints
            write_entry(margins_xmin_entry, '0')
            write_entry(margins_xmax_entry, '0')
            write_entry(margins_ymin_entry, '0')
            write_entry(margins_ymax_entry, '0')
            read_constraints_from_controls()

            # Allow preview playback to start
            IS_PLAYING = True

            __AWAITING_VIDEO = False

            # Process the loaded data automatically
            auto_process()
            # Start the frame update loop
            update_frame()
            return
        else:
            # Enable Model Launch Components
            toggle_all_widgets(MODEL_FRAME, True)

            # Adjust time bounds for the model
            write_entry(end_frame_entry, str(VIDEO_TOTAL_FRAMES))

            # Emphasize the 'Model Launch Components' frame
            MODEL_FRAME.config(background='PaleGreen4')
            return
    # Call this function again after some delay
    ROOT_WINDOW.after(1000, await_file_opened)

def update_frame():
    global VIDEO_CAPTURE, preview_panel, merged_frame, timeline_slider

    if __AWAITING_VIDEO:
        return

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

    read_path_length_from_controls()
    read_zoom_from_controls()
    read_speed_from_controls()
    read_constraints_from_controls()

    start_frame = 0 if PATH_LENGTH is None else max(0, frame_number-PATH_LENGTH)
    fly_paths = video_postprocess.construct_paths(TRIMMED_DATA, frame_number, paths=None, start_frame=start_frame)
    adjusted_frame = video_postprocess.copy_frame(frame)
    video_postprocess.draw_paths_onto_frame(TRIMMED_DATA[frame_number], adjusted_frame, fly_paths)

    if DRAW_CONSTRAINTS:
        video_postprocess.draw_constraints_onto_frame(adjusted_frame, CONSTRAINTS)

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
    process_data()

def process_data():
    global PROCESSED_DATA
    populate_links()
    PROCESSED_DATA = data_postprocess.process_data(STORED_RAW_DATA, LINKS)
    apply_constraints()

def populate_links():
    global links_listbox
    links_listbox.delete(0, tk.END)
    for swapped, actual in LINKS.items():
        links_listbox.insert(tk.END, f'{swapped:<5}->{actual:>5}')

def apply_constraints():
    global TRIMMED_DATA
    TRIMMED_DATA = data_postprocess.apply_constraints(PROCESSED_DATA, CONSTRAINTS)

def list_add():
    global LINKS, PROCESSED_DATA, links_listbox
    ans = simpledialog.askstring("Input", "Enter 2 IDs to merge:")
    if ans is None:
        return
    
    ids = [int(num) for num in re.findall(r'\d+', ans)]

    swapped, actual = max(ids), min(ids)
    LINKS[swapped] = actual
    process_data()

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
    process_data()

def list_del():
    global LINKS, PROCESSED_DATA, links_listbox
    selected_index = links_listbox.curselection()
    if not selected_index:
        return
    current_value: str = links_listbox.get(selected_index)
    swapped, actual = current_value.replace('->', ' ').split(maxsplit=2)
    del LINKS[int(swapped)]
    process_data()

def export_csv():
    video_file   = file_helper.get_basename(__INPUT_VIDEO)
    video_folder = __INPUT_VIDEO.replace(video_file, '')
    file_name = file_helper.get_basename_stem(__INPUT_VIDEO)
    output_path = file_helper.join_paths(video_folder, file_name)
    try:
        storage_helper.write_to_csv(TRIMMED_DATA, f'{output_path}_result.csv')
        messagebox.showinfo('Success', f'Exported file to:\n{output_path}_result.csv')
    except:
        messagebox.showerror('Error', 'Failed to export CSV file!')

def export_mp4():
    video_file   = file_helper.get_basename(__INPUT_VIDEO)
    video_folder = __INPUT_VIDEO.replace(video_file, '')
    file_name = file_helper.get_basename_stem(__INPUT_VIDEO)
    output_path = file_helper.join_paths(video_folder, file_name)
    try:
        video_postprocess.annotate_video(TRIMMED_DATA, __INPUT_VIDEO, f'{output_path}_result.mp4', None, False)
        messagebox.showinfo('Success', f'Exported file to:\n{output_path}_result.mp4')
    except:
        messagebox.showerror('Error', 'Failed to export MP4 file!')

def toggle_all_widgets(frame, state: bool):
    for child in frame.winfo_children():
        if child.winfo_children():
            toggle_all_widgets(child, state)
        try:
            child.config(state=tk.NORMAL if state else tk.DISABLED)
        except tk.TclError:
            pass

def import_video():
    global __INPUT_VIDEO, import_avi_button

    file_path = filedialog.askopenfilename(
        title="Select a Video File",
        filetypes=(("Video files", "*.avi"), ("All files", "*.*"))
    )
    if file_path is not None and file_path != '':
        toggle_all_widgets(import_avi_button, False)
        __INPUT_VIDEO = file_path

def reset_variables():
    global __INPUT_VIDEO, TRIMMED_DATA, DRAW_CONSTRAINTS, CONSTRAINTS, PATH_LENGTH
    global LINKS, PROCESSED_DATA, STORED_RAW_DATA, VIDEO_CAPTURE, VIDEO_TOTAL_FRAMES
    global IS_PLAYING, ZOOM_SCALAR, PLAYBACK_DELAY_MS, timeline_slider, preview_panel

    __INPUT_VIDEO = None
    LINKS = {}
    PROCESSED_DATA = None
    STORED_RAW_DATA = None
    TRIMMED_DATA = None

    if VIDEO_CAPTURE is not None:
        VIDEO_CAPTURE.release()
    
    VIDEO_CAPTURE = None
    VIDEO_TOTAL_FRAMES = 0
    IS_PLAYING = False
    ZOOM_SCALAR = 2.2
    PLAYBACK_DELAY_MS = 100
    PATH_LENGTH = None

    timeline_slider.config(to=0)
    preview_panel.imgtk = None
    preview_panel.config(image=None)
    toggle_all_widgets(import_avi_button, True)

    DRAW_CONSTRAINTS = True
    CONSTRAINTS['x_min'] = None
    CONSTRAINTS['x_max'] = None
    CONSTRAINTS['y_min'] = None
    CONSTRAINTS['y_max'] = None
    return

def reset_app():
    global __AWAITING_VIDEO
    reset_variables()

    if not __AWAITING_VIDEO:
        __AWAITING_VIDEO = True
        await_file_opened()
    return

def toggle_constraints():
    global DRAW_CONSTRAINTS
    DRAW_CONSTRAINTS = not DRAW_CONSTRAINTS

def read_constraints_from_controls():
    global CONSTRAINTS
    global margins_xmin_entry, margins_xmax_entry
    global margins_ymin_entry, margins_ymax_entry

    # get video dimensions
    width  = int(VIDEO_CAPTURE.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(VIDEO_CAPTURE.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # try reading values
    x_min = read_entry(margins_xmin_entry)
    x_max = read_entry(margins_xmax_entry)
    y_min = read_entry(margins_ymin_entry)
    y_max = read_entry(margins_ymax_entry)

    # replace failed values
    x_min = x_min if x_min is not None else 0
    x_max = x_max if x_max is not None else 0
    y_min = y_min if y_min is not None else 0
    y_max = y_max if y_max is not None else 0

    # clamp results of converting margins to actual constraints
    CONSTRAINTS['x_min'] = data_postprocess.clamp(x_min        ,  0, width-1)
    CONSTRAINTS['x_max'] = data_postprocess.clamp(width-x_max-1,  0, width-1)
    CONSTRAINTS['y_min'] = data_postprocess.clamp(y_min,          0, height-1)
    CONSTRAINTS['y_max'] = data_postprocess.clamp(height-y_max-1, 0, height-1)

    # invert constraints if they got inverget by large margins (safeguard for user error)
    if CONSTRAINTS['x_max'] < CONSTRAINTS['x_min']:
        CONSTRAINTS['x_max'], CONSTRAINTS['x_min'] = CONSTRAINTS['x_min'], CONSTRAINTS['x_max']
    if CONSTRAINTS['y_max'] < CONSTRAINTS['y_min']:
        CONSTRAINTS['y_max'], CONSTRAINTS['y_min'] = CONSTRAINTS['y_min'], CONSTRAINTS['y_max']

def run_model(input_path: str, start_frame: int, end_frame: int):
    global __INPUT_VIDEO, __AWAITING_VIDEO

    start_time = time.time()
    model_process = subprocess.Popen(
        [__MODEL_EXE, input_path, str(start_frame), str(end_frame)],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    model_process.wait()
    elapsed_time = time.time() - start_time

    # notify the user about the completion
    formatted_time = time.strftime('%M:%S', time.gmtime(elapsed_time))
    if model_process.returncode == 0:
        messagebox.showinfo('Success', f'Analysis Complete!\nElapsed Time: {formatted_time}')
    else:
        messagebox.showerror('Error', f'Analysis Failed!\nElapsed Time: {formatted_time}')
        return

    # force reset the app
    reset_variables()
    toggle_all_widgets(import_avi_button, False)
    __INPUT_VIDEO = input_path
    __AWAITING_VIDEO = False
    await_file_opened()

def run_model_wrapper():
    # get start and end frames from entries
    start_frame = read_entry(start_frame_entry)
    end_frame   = read_entry(end_frame_entry)

    # verify start and end times (safeguard for user error)
    if end_frame < start_frame:
        messagebox.showerror('Error', 'Please ensure valid inputs,\n`start frame` can not be greater than `end frame`.')
    if start_frame < 0 or end_frame < 0:
        messagebox.showerror('Error', 'Please ensure valid inputs,\nneither `start frame` nor `end frame` can be negative.')

    # # check if preview is active, it may cause issues  # TODO: crashing here (pretty sure) due to VIDEO_CAPTURE being reset in reset_variables() while being used in update_frame()
    # #                                                  #       maybe stop update_frame() and restart once done? urghhhhh, just don't run if _raw.csv exists lol
    # if VIDEO_CAPTURE is not None:
    #     messagebox.showwarning('Warning', f'Running analysis while preview is active might cause issues.\n\nIf you encounter any issues, try pressing `Reset`.\n\nIf resetting the application does not help, please manually delete `{file_helper.get_basename_stem(__INPUT_VIDEO)}_raw.csv` and restart the application.')

    # Remove emphasis from 'Model Launch Components' frame
    MODEL_FRAME.config(background=FT_CONTROL_FRAME.cget('bg'))

    # Disable the button to prevent running more than once at a time
    toggle_all_widgets(model_run_button, False)

    # Run the model on a separate thread
    threading.Thread(target=run_model, args=(__INPUT_VIDEO, start_frame, end_frame)).start()

# def insert_path_point(id, frame_number, x, y):  # TODO
#     global PROCESSED_DATA

#     if frame_number not in PROCESSED_DATA.keys():
#         return
    
#     # apply scaling to the given coordinates
#     x /= ZOOM_SCALAR
#     y /= ZOOM_SCALAR

#     tracks = TRIMMED_DATA[frame_number]
#     selected_track = None
#     for track in tracks:
#         if track[0] == id:
#             selected_track = track
#             break

#     if selected_track is None:
#         return
    
#     _, _, x1, y1, x2, y2 = selected_track
#     fx = (x1 + x2)/2
#     fy = (y1 + y2)/2
#     print(f'clicked: {x} {y}')
#     print(f'fly pos: {fx} {fy}')
#     print (selected_track)
#     #if id not in PROCESSED_DATA[frame_number]

# def allow_path_editing():  # TODO
#     id = read_entry(_entry)
#     if id is None:
#         id = 0
#     frame_number = VIDEO_CAPTURE.get(cv2.CAP_PROP_POS_FRAMES)
#     preview_panel.bind("<Button-1>", lambda event: insert_path_point(id, frame_number, event.x, event.y))
    

# read raw data from csv file
LINKS = {}
PROCESSED_DATA = None
STORED_RAW_DATA = None
TRIMMED_DATA = None

# Initialize the video capture
VIDEO_CAPTURE = None
VIDEO_TOTAL_FRAMES = 0
IS_PLAYING = False
ZOOM_SCALAR = 2.2
PLAYBACK_DELAY_MS = 100
PATH_LENGTH = None

# constraint variables
DRAW_CONSTRAINTS = True
CONSTRAINTS = {
    'y_min': None,
    'y_max': None,
    'x_min': None,
    'x_max': None
}



# Initialize tk window
ROOT_WINDOW = tk.Tk()
ROOT_WINDOW.title("Effect Preview")
ROOT_WINDOW.state('zoomed')

# Set the default font for all widgets
monospace_font = font.Font(family='Courier', size=12)
ROOT_WINDOW.option_add("*Font", monospace_font)



# Create the right root frame
RIGHT_FRAME = tk.Frame(ROOT_WINDOW, bg=__BACKGROUND_DARK)
RIGHT_FRAME.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

PREVIEW_FRAME = tk.Frame(RIGHT_FRAME, bg=RIGHT_FRAME.cget('bg'))
PREVIEW_FRAME.pack(fill=tk.BOTH, expand=True)



# Create the left root frame
LEFT_FRAME = tk.Frame(ROOT_WINDOW, bg=__BACKGROUND_LIGHT)
LEFT_FRAME.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

PREVIEW_CONTROL_FRAME = tk.Frame(LEFT_FRAME, bg=LEFT_FRAME.cget('bg'))
PREVIEW_CONTROL_FRAME.pack(fill=tk.BOTH, expand=False, padx=20, pady=20)

SPACING_FRAME = tk.Frame(LEFT_FRAME, bg=__BACKGROUND_DARK, height=10)
SPACING_FRAME.pack(fill=tk.X, expand=False)

FT_CONTROL_FRAME = tk.Frame(LEFT_FRAME, bg=LEFT_FRAME.cget('bg'))
FT_CONTROL_FRAME.pack(fill=tk.BOTH, expand=False)

SPACING_FRAME = tk.Frame(LEFT_FRAME, bg=__BACKGROUND_DARK, height=10)
SPACING_FRAME.pack(fill=tk.X, expand=False)

DATA_CONTROL_FRAME = tk.Frame(LEFT_FRAME, bg=LEFT_FRAME.cget('bg'))
DATA_CONTROL_FRAME.pack(fill=tk.BOTH, expand=True)

SPACING_FRAME = tk.Frame(LEFT_FRAME, bg=__BACKGROUND_DARK, height=10)
SPACING_FRAME.pack(fill=tk.X, expand=False)

EXTERNAL_FRAME = tk.Frame(LEFT_FRAME, bg=LEFT_FRAME.cget('bg'))
EXTERNAL_FRAME.pack(fill=tk.BOTH, expand=False, padx=20, pady=20)


# Create FlyTracker sub frames
MARGINS_FRAME = tk.Frame(FT_CONTROL_FRAME, bg=FT_CONTROL_FRAME.cget('bg'))
MARGINS_FRAME.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=20, pady=20)

SPACING_FRAME = tk.Frame(FT_CONTROL_FRAME, bg=__BACKGROUND_DARK, width=10)
SPACING_FRAME.pack(side=tk.LEFT, fill=tk.Y, expand=False)

MODEL_FRAME = tk.Frame(FT_CONTROL_FRAME, bg=FT_CONTROL_FRAME.cget('bg'))
MODEL_FRAME.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=20, pady=20)

# Create DataControl sub frames
LINKS_CONTROL_FRAME = tk.Frame(DATA_CONTROL_FRAME, bg=DATA_CONTROL_FRAME.cget('bg'))
LINKS_CONTROL_FRAME.pack(side=tk.LEFT, fill=tk.BOTH, padx=20, pady=20, expand=False)

# SPACING_FRAME = tk.Frame(DATA_CONTROL_FRAME, bg=__BACKGROUND_DARK, width=10)  # TODO
# SPACING_FRAME.pack(side=tk.LEFT, fill=tk.Y, expand=False)

# PATHS_CONTROL_FRAME = tk.Frame(DATA_CONTROL_FRAME, bg=DATA_CONTROL_FRAME.cget('bg'))
# PATHS_CONTROL_FRAME.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)

# Create External sub frames
IMPORT_BUTTONS_FRAME = tk.Frame(EXTERNAL_FRAME, bg=EXTERNAL_FRAME.cget('bg'))
IMPORT_BUTTONS_FRAME.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

EXPORT_BUTTONS_FRAME = tk.Frame(EXTERNAL_FRAME, bg=EXTERNAL_FRAME.cget('bg'))
EXPORT_BUTTONS_FRAME.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)



# Preview Components
preview_panel = tk.Label(PREVIEW_FRAME, bg=PREVIEW_FRAME.cget('bg'))
preview_panel.pack()

timeline_slider = tk.Scale(PREVIEW_FRAME, from_=0, to=VIDEO_TOTAL_FRAMES, orient=tk.HORIZONTAL)
timeline_slider.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)



# Preview Control Components
controls_label = ttk.Label(PREVIEW_CONTROL_FRAME, text='Preview controls:')
controls_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.EW)

play_preview_button = tk.Button(PREVIEW_CONTROL_FRAME, width=12, text="Play", command=resume_preview)
play_preview_button.grid(row=0, column=1, padx=5, pady=5)

pause_preview_button = tk.Button(PREVIEW_CONTROL_FRAME, width=12, text="Pause", command=pause_preview)
pause_preview_button.grid(row=0, column=2, padx=5, pady=5)

restart_preview_button = tk.Button(PREVIEW_CONTROL_FRAME, width=12, text="Restart", command=restart_preview)
restart_preview_button.grid(row=0, column=3, padx=5, pady=5)

zoom_label = ttk.Label(PREVIEW_CONTROL_FRAME, text='Zoom level [%]:')
zoom_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.EW)
zoom_slider = tk.Scale(PREVIEW_CONTROL_FRAME, from_=50, to=250, orient=tk.HORIZONTAL)
zoom_slider.set(ZOOM_SCALAR * 100)
zoom_slider.grid(row=1, column=1, columnspan=3, pady=5, sticky=tk.EW)

speed_label = ttk.Label(PREVIEW_CONTROL_FRAME, text='Playback speed [%]:')
speed_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.EW)
speed_slider = tk.Scale(PREVIEW_CONTROL_FRAME, from_=10, to=200, orient=tk.HORIZONTAL)
speed_slider.set(100)
speed_slider.grid(row=2, column=1, columnspan=3, pady=5, sticky=tk.EW)

path_length_label = ttk.Label(PREVIEW_CONTROL_FRAME, text='Tracks length [frames]:')
path_length_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.EW)
path_length_entry = tk.Entry(PREVIEW_CONTROL_FRAME, width=12)
write_entry(path_length_entry, '-1')
path_length_entry.grid(row=3, column=1, pady=5)



# Margins Control Components
margins_ymin_label = ttk.Label(MARGINS_FRAME, text='Top [px]:')
margins_ymin_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.EW)
margins_ymin_entry = tk.Entry(MARGINS_FRAME)
margins_ymin_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

margins_ymax_label = ttk.Label(MARGINS_FRAME, text='Bottom [px]:')
margins_ymax_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.EW)
margins_ymax_entry = tk.Entry(MARGINS_FRAME)
margins_ymax_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

margins_xmin_label = ttk.Label(MARGINS_FRAME, text='Left [px]:')
margins_xmin_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.EW)
margins_xmin_entry = tk.Entry(MARGINS_FRAME)
margins_xmin_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

margins_xmax_label = ttk.Label(MARGINS_FRAME, text='Right [px]:')
margins_xmax_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.EW)
margins_xmax_entry = tk.Entry(MARGINS_FRAME)
margins_xmax_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

margins_view_button = tk.Button(MARGINS_FRAME, text="Show/Hide\nConstraints", width=18, command=toggle_constraints)
margins_view_button.grid(row=4, column=0, padx=5, pady=5, sticky=tk.EW)

apply_constraints_button = tk.Button(MARGINS_FRAME, text="Apply\nConstraints", width=18, command=apply_constraints)
apply_constraints_button.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)



# Model Launch Components
start_frame_label = ttk.Label(MODEL_FRAME, text='Start frame:')
start_frame_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.EW)
start_frame_entry = tk.Entry(MODEL_FRAME)
write_entry(start_frame_entry, '0')
start_frame_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

end_frame_label = ttk.Label(MODEL_FRAME, text='End frame:')
end_frame_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.EW)
end_frame_entry = tk.Entry(MODEL_FRAME)
write_entry(end_frame_entry, '0')
end_frame_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

model_run_button = tk.Button(MODEL_FRAME, text="Run Model", width=18, command=run_model_wrapper)
model_run_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)



# Link Control Components
links_label = tk.Label(LINKS_CONTROL_FRAME, text='Links:')
links_label.grid(row=0, column=0, pady=5, sticky=tk.W)

list_add_button = tk.Button(LINKS_CONTROL_FRAME, text="Add", width=8, command=list_add)
list_add_button.grid(row=0, column=1, pady=5, sticky=tk.E)

list_edt_button = tk.Button(LINKS_CONTROL_FRAME, text="Edit", width=8, command=list_edt)
list_edt_button.grid(row=0, column=2, pady=5, sticky=tk.E)

list_del_button = tk.Button(LINKS_CONTROL_FRAME, text="Remove", width=8, command=list_del)
list_del_button.grid(row=0, column=3, pady=5, sticky=tk.E)

links_listbox = tk.Listbox(LINKS_CONTROL_FRAME)
links_listbox.grid(row=1, column=0, columnspan=4, pady=5, sticky=tk.EW)

gap_label = ttk.Label(LINKS_CONTROL_FRAME, text='Gap threshold [px]:')
gap_label.grid(row=2, column=0, columnspan=2, padx=(0, 5), pady=5, sticky=tk.W)
gap_entry = tk.Entry(LINKS_CONTROL_FRAME)
write_entry(gap_entry, '3')
gap_entry.grid(row=2, column=2, columnspan=2, padx=(5, 0), pady=5, sticky=tk.E)

auto_button = tk.Button(LINKS_CONTROL_FRAME, text="Automatically find links", command=auto_process)
auto_button.grid(row=3, column=0, columnspan=4, pady=5, sticky=tk.EW)



# # Fly Path Modification Components  # TODO
# _entry = tk.Entry(PATHS_CONTROL_FRAME)
# write_entry(_entry, '3')
# _entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

# _button = tk.Button(PATHS_CONTROL_FRAME, text="EDIT FLY PATHS", command=allow_path_editing)
# _button.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)



# Import/Export Components
import_avi_button = tk.Button(IMPORT_BUTTONS_FRAME, text="Import Video", command=import_video)
import_avi_button.grid(row=0, column=0, padx=5, pady=5, sticky=tk.SE)

reset_app_button = tk.Button(IMPORT_BUTTONS_FRAME, text="Reset", command=reset_app)
reset_app_button.grid(row=0, column=1, padx=5, pady=5, sticky=tk.SE)

export_cvs_button = tk.Button(EXPORT_BUTTONS_FRAME, text="Export to CSV", command=export_csv)
export_cvs_button.grid(row=0, column=0, padx=5, pady=5, sticky=tk.SE)

export_mp4_button = tk.Button(EXPORT_BUTTONS_FRAME, text="Export to MP4", command=export_mp4)
export_mp4_button.grid(row=0, column=1, padx=5, pady=5, sticky=tk.SE)



# Add event listeners
ROOT_WINDOW.bind("<Button-1>", deselect_all_entries)

# Disable elements until loaded a video
toggle_all_widgets(RIGHT_FRAME, False)
toggle_all_widgets(PREVIEW_CONTROL_FRAME, False)
toggle_all_widgets(FT_CONTROL_FRAME, False)
toggle_all_widgets(DATA_CONTROL_FRAME, False)
toggle_all_widgets(EXPORT_BUTTONS_FRAME, False)

await_file_opened()

# Start the tk event loop
ROOT_WINDOW.mainloop()

# Release the video capture object
if VIDEO_CAPTURE is not None:
    VIDEO_CAPTURE.release()
