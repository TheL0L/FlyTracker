# FlyTracker

FlyTracker is a Python-based tool that utilizes YOLOv8 and DeepSort to track multiple flies in videos.

*Note: As for this moment, the YOLO weights are **not** included in the repository.*

## Usage

1. Clone the repository:

   ```
   git clone https://github.com/TheL0L/FlyTracker.git
   cd FlyTracker
   ```

2. Set up a virtual environment:

   ```
   python -m venv .venv
   ```

3. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Run the FlyTracker graphical interface:

   ```
   python track_editor_qt.py
   ```

## CUDA Support

FlyTracker can leverage CUDA devices for faster processing. However, to enable CUDA support, you need to set up `torch-cuda` and `cuda-toolkit` on your machine. Refer to the [official documentation](https://docs.nvidia.com/cuda/cuda-quick-start-guide/index.html) for instructions on setting up CUDA support.

## Acknowledgments

- YOLOv8: [Link to YOLOv8 repository](https://github.com/ultralytics/ultralytics)
- DeepSort: [Link to DeepSort repository](https://github.com/levan92/deep_sort_realtime)

