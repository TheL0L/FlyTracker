# FlyTracker

FlyTracker is a Python-based tool that utilizes YOLOv8 and DeepSort to track multiple flies in videos.

## Dependencies

FlyTracker requires Python 3.12 and the following dependencies, which are also listed in the `requirements.txt` file:

- deep-sort-realtime==1.3.2
- opencv-python==4.9.0.80
- torch==2.2.2
- tqdm==4.66.2
- ultralytics==8.1.47

## Usage

To use FlyTracker, follow these steps:

1. Clone the repository:

   ```
   git clone https://github.com/TheL0L/FlyTracker.git
   ```

2. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Run the FlyTracker:

   ```
   TODO
   ```

## CUDA Support

FlyTracker can leverage CUDA devices for faster processing. However, to enable CUDA support, you need to set up `torch-cuda` and `cuda-toolkit` on your machine. Refer to the official documentation for instructions on setting up CUDA support.

## Acknowledgments

- YOLOv8: [Link to YOLOv8 repository](https://github.com/ultralytics/ultralytics)
- DeepSort: [Link to DeepSort repository](https://github.com/levan92/deep_sort_realtime)

