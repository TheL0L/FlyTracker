from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import torch


class FlyTracker:
    """
    A class for detecting and tracking flies using YOLOv8 and DeepSort.

    Args:
        model_path (str): The path to the YOLO model weights and configuration.
        track_max_age (int, optional): Maximum age of a track before it is considered invalid. Defaults to 10.
        confidence_threshold (float, optional): Confidence threshold for YOLO detections. Defaults to 0.

    Attributes:
        detector: YOLO object detector.
        tracker: DeepSort tracker.
        confidence_threshold (float): Confidence threshold for YOLO detections.
        constraints (dict): Constraints for filtering tracked objects based on their coordinates.
    """

    def __init__(self, model_path, track_max_age=10, confidence_threshold=0) -> None:
        """
        Initializes the FlyTracker.

        Args:
            model_path (str): The path to the YOLO model weights and configuration.
            track_max_age (int, optional): Maximum age of a track before it is considered invalid. Defaults to 10.
            confidence_threshold (float, optional): Confidence threshold for YOLO detections. Defaults to 0.
        """
        self.detector = YOLO(model_path)
        self.tracker = DeepSort(max_age=track_max_age)

        self.__device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.detector.to(self.__device)

        self.confidence_threshold = max(min(confidence_threshold, 1), 0)
        self.constraints = {'x_min': None, 'x_max': None, 'y_min': None, 'y_max': None}

    def set_constraints(self, x_min=None, x_max=None, y_min=None, y_max=None) -> None:
        """
        Set constraints for filtering tracked objects based on their coordinates.

        Args:
            x_min (float, optional): Minimum x-coordinate. Defaults to None.
            x_max (float, optional): Maximum x-coordinate. Defaults to None.
            y_min (float, optional): Minimum y-coordinate. Defaults to None.
            y_max (float, optional): Maximum y-coordinate. Defaults to None.
        """
        if x_min is not None:
            self.constraints['x_min'] = x_min
        if x_max is not None:
            self.constraints['x_max'] = x_max
        if y_min is not None:
            self.constraints['y_min'] = y_min
        if y_max is not None:
            self.constraints['y_max'] = y_max

    @staticmethod
    def __yolo2sort(yolo_result) -> tuple:
        """
        Convert YOLO detection results to DeepSort format.

        Args:
            yolo_result (list): YOLO detection result.

        Returns:
            tuple: Detection in DeepSort format.
        """
        x1, y1, x2, y2, score, class_id = yolo_result
        return [x1, y1, x2 - x1, y2 - y1], score, class_id

    @staticmethod
    def __sort2result(track) -> tuple:
        """
        Convert DeepSort track to result format.

        Args:
            track: DeepSort track.

        Returns:
            tuple: Tracking result.
        """
        x1, y1, w, h = track.to_ltwh()
        x2, y2 = x1 + w, y1 + h
        return int(track.track_id), track.get_det_conf(), x1, y1, x2, y2

    def __apply_constraints(self, track) -> bool:
        """
        Apply constraints to a tracked object.

        Args:
            track: Tracked object.

        Returns:
            bool: True if the tracked object satisfies the constraints, False otherwise.
        """
        _, _, x1, y1, x2, y2 = track
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        return (
            ((self.constraints['x_min'] is None) or (mid_x >= self.constraints['x_min'])) and
            ((self.constraints['x_max'] is None) or (mid_x <= self.constraints['x_max'])) and
            ((self.constraints['y_min'] is None) or (mid_y >= self.constraints['y_min'])) and
            ((self.constraints['y_max'] is None) or (mid_y <= self.constraints['y_max']))
        )

    def detect(self, frame) -> list:
        """
        Detect and track flies in a frame.

        Args:
            frame: Image frame.

        Returns:
            list: List of tracked objects satisfying the constraints.
        """
        # pass the image through the yolo model
        results = self.detector(frame, verbose=False)[0]

        # preproccess the detections for deepsort
        detections = [self.__yolo2sort(result) for result in results.boxes.data.tolist()]

        # exclude detections under the confidence threshold
        if self.confidence_threshold > 0:
            detections = [d for d in detections if d[1] >= self.confidence_threshold]

        # pass the detections through the deepsort model
        tracks = self.tracker.update_tracks(raw_detections=detections, frame=frame)

        # exclude invalid tracks
        tracks = filter(lambda t: t.is_confirmed(), tracks)

        # reformat the tracking results
        tracks = [self.__sort2result(t) for t in tracks]

        tracks = filter(lambda t: self.__apply_constraints(t), tracks)
        return list(tracks)

    def reset_tracking(self) -> None:
        """
        Reset the tracker by deleting all tracks.
        """
        self.tracker.delete_all_tracks()

