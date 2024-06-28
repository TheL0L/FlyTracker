import tkinter as tk
import numpy as np
import cv2
from PIL import Image, ImageTk
import file_helper
from datetime import datetime
import os
import video_preprocess

__INPUT_VIDEO = './testing_snap.png'
__OUTPUT_PATH = './effect_previews/'

__ZOOM_SCALAR = 1.2
__PLAYBACK_DELAY_MS = 30
__R_LUT_SIZE, __G_LUT_SIZE, __B_LUT_SIZE = 5, 5, 5


__R_LUT_X, __R_LUT_Y = list(np.arange(0, 255, __R_LUT_SIZE, dtype='uint8')), list(np.arange(0, 255, __R_LUT_SIZE, dtype='uint8'))
__G_LUT_X, __G_LUT_Y = list(np.arange(0, 255, __G_LUT_SIZE, dtype='uint8')), list(np.arange(0, 255, __G_LUT_SIZE, dtype='uint8'))
__B_LUT_X, __B_LUT_Y = list(np.arange(0, 255, __B_LUT_SIZE, dtype='uint8')), list(np.arange(0, 255, __B_LUT_SIZE, dtype='uint8'))



def save_preview() -> None:
    global merged_frame
    # Convert the frame to RGB before saving
    rgb_frame = cv2.cvtColor(merged_frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb_frame)

    # Prepare output path
    current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_helper.prepare_output_path(__OUTPUT_PATH)
    filename = os.path.join(__OUTPUT_PATH, f"frame_{current_datetime}.png")
    
    # Save the image
    img.save(filename)
    print(f'Saved preview as: {filename}')

def save_luts() -> None:
    global merged_frame

    # Prepare output path
    current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_helper.prepare_output_path(__OUTPUT_PATH)
    filename = os.path.join(__OUTPUT_PATH, f"LUTs_{current_datetime}.txt")
    
    with open(filename, 'w', encoding='utf-8') as writer:
        writer.write('# RED LUT\n')
        writer.write(f'{__R_LUT_X=}\n')
        writer.write(f'{__R_LUT_Y=}\n')
        writer.write('\n# GREEN LUT\n')
        writer.write(f'{__G_LUT_X=}\n')
        writer.write(f'{__G_LUT_Y=}\n')
        writer.write('\n# BLUE LUT\n')
        writer.write(f'{__B_LUT_X=}\n')
        writer.write(f'{__B_LUT_Y=}\n')
    
    print(f'Saved LUTs as: {filename}')

def add_sliders(root_frame : tk.Frame, count : int) -> list:
    sliders = []
    x_entries = []

    start_values = list(np.linspace(0, 255, count, dtype=int))
    for i in range(count):
        slider_frame = tk.Frame(root_frame, bg=root_frame.cget("bg"))
        slider_frame.pack(side=tk.LEFT, padx=2, pady=2)
        
        # x value textbox
        x_entry = tk.Entry(slider_frame, width=5)
        x_entry.insert(0, str(start_values[i]))
        x_entry.pack(anchor='center')
        x_entries.append(x_entry)
        
        # y value slider
        slider = tk.Scale(slider_frame, from_=255, to=0, orient=tk.VERTICAL, length=200)
        slider.set(start_values[i])
        slider.pack(anchor='center')
        sliders.append(slider)
    return sliders, x_entries

def deselect_all_entries(event):
    widget = event.widget
    if not isinstance(widget, tk.Entry):
        root.focus()

def restart_preview():
    global VIDEO_CAPTURE
    VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, 0)

def preprocess_frame(frame):
    lut_r = video_preprocess.create_lut_8uc1(__R_LUT_X, __R_LUT_Y)
    lut_g = video_preprocess.create_lut_8uc1(__G_LUT_X, __G_LUT_Y)
    lut_b = video_preprocess.create_lut_8uc1(__B_LUT_X, __B_LUT_Y)

    adjusted_frame = video_preprocess.apply_curves_to_channels(frame, lut_r, lut_g, lut_b)
    adjusted_frame = video_preprocess.to_grayscale_3c(adjusted_frame)
    return adjusted_frame

def read_luts_from_controls():
    global __R_LUT_X, __R_LUT_Y
    global __G_LUT_X, __G_LUT_Y
    global __B_LUT_X, __B_LUT_Y

    __R_LUT_X, __R_LUT_Y = [int(e.get()) for e in R_ENTRIES], [s.get() for s in R_SLIDERS]
    __G_LUT_X, __G_LUT_Y = [int(e.get()) for e in G_ENTRIES], [s.get() for s in G_SLIDERS]
    __B_LUT_X, __B_LUT_Y = [int(e.get()) for e in B_ENTRIES], [s.get() for s in B_SLIDERS]

def read_zoom_from_controls():
    global __ZOOM_SCALAR

    __ZOOM_SCALAR = zoom_slider.get() / 100

def update_frame():
    global VIDEO_CAPTURE, panel, merged_frame

    ret, frame = VIDEO_CAPTURE.read()
    if not ret:
        VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Restart video
        ret, frame = VIDEO_CAPTURE.read()

    read_luts_from_controls()
    read_zoom_from_controls()

    # apply effects to frame
    adjusted_frame = preprocess_frame(frame)

    # place adjusted and original frames side by side
    height, width = frame.shape[:2]
    if width < height:
        merged_frame = cv2.hconcat([adjusted_frame, frame])
    else:
        merged_frame = cv2.vconcat([adjusted_frame, frame])

    # Convert the frame to a format that can be used by tk
    img = Image.fromarray(cv2.cvtColor(merged_frame, cv2.COLOR_BGR2RGB))
    resized = img.resize((int(img.width * __ZOOM_SCALAR), int(img.height * __ZOOM_SCALAR)), Image.LANCZOS)
    imgtk = ImageTk.PhotoImage(image=resized)

    # Update the image in the panel
    preview_panel.imgtk = imgtk
    preview_panel.config(image=imgtk)
    
    # Call this function again after some delay
    root.after(__PLAYBACK_DELAY_MS, update_frame)



# Initialize tk window
root = tk.Tk()
root.title("Effect Preview")

# Set the background color and default window size
root.configure(bg='#1E1E1E')
root.geometry("800x400")
root.minsize(400, 300)

# Create the left and right frames
LEFT_FRAME = tk.Frame(root, bg='DimGray')
LEFT_FRAME.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

RIGHT_FRAME = tk.Frame(root, width=200, height=200)
RIGHT_FRAME.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)



# Add preview panel to the left frame
preview_panel = tk.Label(LEFT_FRAME)
preview_panel.pack(side=tk.LEFT)

# Create four vertically stacked control frames inside the right frame
R_CONTROL_FRAME = tk.Frame(RIGHT_FRAME, bg='Red')
R_CONTROL_FRAME.pack(fill=tk.BOTH, expand=True)

G_CONTROL_FRAME = tk.Frame(RIGHT_FRAME, bg='Green')
G_CONTROL_FRAME.pack(fill=tk.BOTH, expand=True)

B_CONTROL_FRAME = tk.Frame(RIGHT_FRAME, bg='Blue')
B_CONTROL_FRAME.pack(fill=tk.BOTH, expand=True)

O_CONTROL_FRAME = tk.Frame(RIGHT_FRAME, bg='DimGray')
O_CONTROL_FRAME.pack(fill=tk.BOTH, expand=True)

# Add sliders to the color control frames
R_SLIDERS, R_ENTRIES = add_sliders(R_CONTROL_FRAME, __R_LUT_SIZE)
G_SLIDERS, G_ENTRIES = add_sliders(G_CONTROL_FRAME, __G_LUT_SIZE)
B_SLIDERS, B_ENTRIES = add_sliders(B_CONTROL_FRAME, __B_LUT_SIZE)

# Add buttons to additional options frame
restart_preview_button = tk.Button(O_CONTROL_FRAME, text="Restart Preview", command=restart_preview)
restart_preview_button.pack(side=tk.LEFT, padx=2, pady=2)

save_preview_button = tk.Button(O_CONTROL_FRAME, text="Save Preview", command=save_preview)
save_preview_button.pack(side=tk.LEFT, padx=2, pady=2)

save_config_button = tk.Button(O_CONTROL_FRAME, text="Save LUTs", command=save_luts)
save_config_button.pack(side=tk.LEFT, padx=2, pady=2)

zoom_slider = tk.Scale(O_CONTROL_FRAME, from_=10, to=200, orient=tk.HORIZONTAL, length=200)
zoom_slider.set(__ZOOM_SCALAR * 100)
zoom_slider.pack(side=tk.LEFT)


# Add event listeners
root.bind("<Button-1>", deselect_all_entries)


# Initialize the video capture
VIDEO_CAPTURE = cv2.VideoCapture(__INPUT_VIDEO)

# Start the frame update loop
update_frame()

# Start the tk event loop
root.mainloop()

# Release the video capture object
VIDEO_CAPTURE.release()
