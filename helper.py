import os
import cv2

PROJECT_ROOT = 'G:/repos/end_project/'
TRAINED_MODELS_ROOT = './runs/detect/'
CONFIG_FILE  = os.path.join(PROJECT_ROOT, './dataset/data.yaml')


# helper function to find latest train number
def find_last_train():
    path = os.path.join(PROJECT_ROOT, TRAINED_MODELS_ROOT)
    folders = [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
    folders = [folder.replace('train', '') for folder in folders if folder.startswith('train')]
    numbers = [int(folder) for folder in folders if folder != '']
    if numbers:
        return max(numbers)
    else:
        return None

# helper function to get the latest best model weights path
def find_last_best_model_path():
    LATEST_TRAIN_NUMBER = find_last_train()

    WEIGHTS_ROOT = os.path.join(PROJECT_ROOT, f'./runs/detect/train{LATEST_TRAIN_NUMBER}/weights')
    MODEL_FILE   = 'best.pt'

    return os.path.join(PROJECT_ROOT, WEIGHTS_ROOT, MODEL_FILE)

# helper function to create an integer point
def make_point(x, y):
    return int(x), int(y)

# helper function to calculate center point
def get_center(x1, y1, x2, y2):
    return (x1 + x2)/2, (y1 + y2)/2

# helper function to draw points on an image
def draw_points(image, points, color=(0, 255, 0), radius=0, thickness=1):
    for point in points:
        cv2.circle(image, point, radius, color, thickness)

# helper function to draw points and connect them with lines on an image
def draw_points_with_lines(image, points, color=(0, 255, 0), radius=0, thickness=1):
    # draw points
    for point in points:
        int_point = make_point(*point) 
        cv2.circle(image, int_point, radius, color, thickness)
    
    # connect points with lines
    if len(points) > 1:
        for i in range(len(points) - 1):
            int_p1 = make_point(*points[i])
            int_p2 = make_point(*points[i + 1])
            cv2.line(image, int_p1, int_p2, color, thickness)

def rgb_to_bgr(color):
    r, g, b = color
    return b, g, r

def conf_color(conf):
    value = 0 if conf is None else max(0, min(1, conf))
    red = int((1 - value) * 255)
    green = int(value * 255)
    return (red, green, 0)

def id_to_color(id):
    colors = {
        0: (255, 20, 147),
        1: (255, 0, 0),
        2: (0, 255, 0),
        3: (0, 0, 255),
        4: (255, 255, 0),
        5: (255, 0, 255),
        6: (0, 255, 255),
        7: (128, 0, 0),
        8: (0, 128, 0),
        9: (0, 0, 128),
        10: (128, 128, 0),
        11: (128, 0, 128),
        12: (0, 128, 128),
        13: (128, 128, 128),
        14: (192, 192, 192),
        15: (255, 165, 0),
        16: (255, 192, 203),
        17: (255, 99, 71),
        18: (210, 105, 30),
        19: (0, 255, 127),
    }
    if id not in colors:
        return (255, 255, 255)
    return colors[id]
