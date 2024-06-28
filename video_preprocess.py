import cv2
import numpy as np


def create_lut_8uc1(x: list, y: list) -> np.ndarray:
    """
    Creates a look-up table (LUT) for 8-bit single channel image transformation.

    Parameters:
    - x (list): List of original values.
    - y (list): List of corresponding transformed values.

    Returns:
    - numpy.ndarray: Look-Up Table (LUT) for the transformation.
    """
    # Define control points
    original_values = np.array(x)
    new_values = np.array(y)
    
    # Create a LUT
    full_range = np.arange(256, dtype='uint8')
    lut = np.interp(full_range, original_values, new_values)
    
    return lut.astype('uint8')

def apply_curve_to_image(image: np.ndarray, lut) -> np.ndarray:
    """
    Applies a curve transformation to an image using a LUT (Look-Up Table).
    If lut is None, applies a linear transformation.

    Parameters:
    - image (numpy.ndarray): Input image.
    - lut (numpy.ndarray or None): Look-Up Table (LUT) for the transformation. If None, applies linear transformation.

    Returns:
    - numpy.ndarray: Transformed image.
    """
    if lut is None:
        # Apply linear transformation
        lut = np.arange(256, dtype='uint8')
    return cv2.LUT(image, lut)

def apply_curves_to_channels(image: np.ndarray, lut_r, lut_g, lut_b) -> np.ndarray:
    """
    Applies curve transformations to each channel (R, G, B) of an image using respective LUTs.
    If any lut_r, lut_g, or lut_b is None, applies a linear transformation to that channel.

    Parameters:
    - image (numpy.ndarray): Input image.
    - lut_r (numpy.ndarray or None): LUT for the red channel transformation. If None, applies linear transformation.
    - lut_g (numpy.ndarray or None): LUT for the green channel transformation. If None, applies linear transformation.
    - lut_b (numpy.ndarray or None): LUT for the blue channel transformation. If None, applies linear transformation.

    Returns:
    - numpy.ndarray: Image with transformed channels merged back together.
    """
    # Define linear LUT
    linear_lut = np.arange(256, dtype='uint8')
    
    # Apply linear LUT if any LUT is None
    lut_r = lut_r if lut_r is not None else linear_lut
    lut_g = lut_g if lut_g is not None else linear_lut
    lut_b = lut_b if lut_b is not None else linear_lut
    
    # Split the image into its three channels: R, G, and B
    r, g, b = split_to_rgb(image)
    
    # Apply the LUT to each channel
    r = cv2.LUT(r, lut_r)
    g = cv2.LUT(g, lut_g)
    b = cv2.LUT(b, lut_b)
    
    # Merge the channels back into a single image
    return merge_from_rgb(r, g, b)

def to_grayscale_3c(image: np.ndarray) -> np.ndarray:
    """
    Converts a BGR image to grayscale while preserving the 3-channel format.

    Parameters:
    - image (numpy.ndarray): Input BGR image.

    Returns:
    - numpy.ndarray: Grayscale image converted from BGR format.
    """
    return cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)

def split_to_rgb(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Splits an image into its individual R, G, and B channels.

    Parameters:
    - image (numpy.ndarray): Input image in BGR format.

    Returns:
    - tuple: Three numpy arrays representing R, G, and B channels respectively.
    """
    b, g, r = cv2.split(image)
    return r, g, b

def merge_from_rgb(r: np.ndarray, g: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Merges individual R, G, and B channels into a single image.

    Parameters:
    - r (numpy.ndarray): Red channel.
    - g (numpy.ndarray): Green channel.
    - b (numpy.ndarray): Blue channel.

    Returns:
    - numpy.ndarray: Merged image in BGR format.
    """
    return cv2.merge([b, g, r])

