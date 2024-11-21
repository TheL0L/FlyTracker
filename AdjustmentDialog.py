from PyQt5.QtWidgets import QDialog
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QPoint, QRect

class AdjustmentDialog(QDialog):
    """
    A dialog that allows manual adjustment of points over frames in a graphical interface.
    
    Attributes:
        frames (list[QPixmap]): A list of QPixmap objects representing the frames.
        points (list[tuple[int, int]]): A list of tuples representing points for each frame.
        current_frame (int): The index of the currently displayed frame.
        dragging (bool): Indicates if the user is dragging a point.
        drag_margin (int): The margin for detecting point dragging.
        hide_gui (bool): Toggles the visibility of GUI elements.
        scale (int): The scale factor for the display.
    """

    def __init__(self, frames: list[QPixmap], points: list[tuple[int, int]]):
        """
        Initialize the AdjustmentDialog.

        Args:
            frames (list[QPixmap]): List of QPixmap objects representing frames.
            points (list[tuple[int, int]]): List of points corresponding to the frames.
        """
        super().__init__()
        self.frames = frames
        self.points = points
        self.current_frame = 1
        self.dragging = False
        self.drag_margin = 20
        self.hide_gui = False
        self.scale = 2

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle("Manual Path Adjustment")
        self.setFixedSize(frames[0].width() * self.scale, frames[0].height() * self.scale)

    def keyPressEvent(self, event):
        """
        Handle key press events for navigation and settings adjustment.

        Args:
            event (QKeyEvent): The key press event object.
        """
        if event.key() == Qt.Key_Left:
            self.current_frame = max(0, self.current_frame - 1)
            self.update()
        elif event.key() == Qt.Key_Right:
            self.current_frame = min(self.current_frame + 1, len(self.points) - 1)
            self.update()
        elif event.key() == Qt.Key_Space:
            self.hide_gui = not self.hide_gui
            self.update()
        elif event.key() == Qt.Key_Plus:
            self.scale = min(self.scale + 1, 5)
            self.setFixedSize(self.frames[0].width() * self.scale, self.frames[0].height() * self.scale)
            self.update()
        elif event.key() == Qt.Key_Minus:
            self.scale = max(1, self.scale - 1)
            self.setFixedSize(self.frames[0].width() * self.scale, self.frames[0].height() * self.scale)
            self.update()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """
        Handle mouse press events to enable point dragging.

        Args:
            event (QMouseEvent): The mouse press event object.
        """
        current_point = self.getScaledPoint(self.points[self.current_frame])
        drag_rect = QRect(
            current_point.x() - self.drag_margin, current_point.y() - self.drag_margin,
            self.drag_margin * 2, self.drag_margin * 2
        )
        if drag_rect.contains(event.pos()):
            self.dragging = True

    def mouseMoveEvent(self, event):
        """
        Handle mouse move events to update point positions while dragging.

        Args:
            event (QMouseEvent): The mouse move event object.
        """
        if self.dragging:
            if self.current_frame in [0, len(self.frames) - 1]:
                return  # Ignore static point frames
            self.points[self.current_frame] = (
                int(event.pos().x() / self.scale),
                int(event.pos().y() / self.scale)
            )
            self.update()

    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events to stop point dragging.

        Args:
            event (QMouseEvent): The mouse release event object.
        """
        self.dragging = False

    def getScaledFrame(self, frame_number) -> QPixmap:
        """
        Get a scaled version of a specific frame.

        Args:
            frame_number (int): The index of the frame to scale.

        Returns:
            QPixmap: The scaled frame.
        """
        pixmap = self.frames[frame_number]
        return pixmap.scaled(
            int(pixmap.width() * self.scale),
            int(pixmap.height() * self.scale),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

    def getScaledPoint(self, point: tuple[int, int]) -> QPoint:
        """
        Scale a point's coordinates based on the current scale.

        Args:
            point (tuple[int, int]): The original point.

        Returns:
            QPoint: The scaled point.
        """
        return QPoint(point[0] * self.scale, point[1] * self.scale)

    def paintEvent(self, event):
        """
        Handle paint events to render the frame, path, and points.

        Args:
            event (QPaintEvent): The paint event object.
        """
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.getScaledFrame(self.current_frame))
        self.drawFrameNumber(painter)
        if not self.hide_gui:
            self.draw_path(painter)
            self.draw_points(painter)

    def drawFrameNumber(self, painter: QPainter):
        """
        Draw the current frame number on the dialog.

        Args:
            painter (QPainter): The painter used for drawing.
        """
        font = self.font()
        font.setPointSize(font.pointSize() + 6)
        painter.setFont(font)

        margin = 10
        padding = 5
        text = f'+{self.current_frame:0>{int(len(self.points) / 10) + 1}}'

        text_rect = self.rect().adjusted(margin, margin, -margin, -margin)
        background_rect = painter.boundingRect(text_rect, Qt.AlignLeft | Qt.AlignTop, text)
        background_rect = background_rect.adjusted(-padding, -padding, padding, padding)

        painter.setBrush(Qt.white)
        painter.setPen(Qt.NoPen)
        painter.drawRect(background_rect)

        painter.setPen(QColor(0, 0, 255))
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignTop, text)

    def draw_path(self, painter: QPainter) -> None:
        """
        Draw the path connecting all points.

        Args:
            painter (QPainter): The painter used for drawing.
        """
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        last = self.getScaledPoint(self.points[0])
        for x in range(1, len(self.points)):
            current = self.getScaledPoint(self.points[x])
            painter.drawLine(last, current)
            last = current

    def draw_points(self, painter: QPainter) -> None:
        """
        Draw all points with distinct styles for different states.

        Args:
            painter (QPainter): The painter used for drawing.
        """
        painter.setPen(QColor(0, 0, 0, 127))
        for x in range(len(self.points)):
            point = self.getScaledPoint(self.points[x])
            if x in [0, len(self.points) - 1]:
                painter.setBrush(QColor(0, 255, 0, 63))
                painter.drawEllipse(point, 8, 8)
            elif x == self.current_frame:
                painter.setBrush(QColor(255, 0, 0, 127))
                painter.drawEllipse(point, self.drag_margin, self.drag_margin)
            else:
                painter.setBrush(QColor(255, 0, 0, 63))
                painter.drawEllipse(point, 8, 8)

    def get_points(self) -> list[tuple[int, int]]:
        """
        Retrieve the list of adjusted points.

        Returns:
            list[tuple[int, int]]: The adjusted points.
        """
        return self.points

    def closeEvent(self, event):
        """
        Handle the close event and accept the dialog.

        Args:
            event (QCloseEvent): The close event object.
        """
        self.accept()
        super().closeEvent(event)
