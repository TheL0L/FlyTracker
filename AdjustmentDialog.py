from PyQt5.QtWidgets import QDialog
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QPoint, QRect


class AdjustmentDialog(QDialog):
    def __init__(self, frames: list[QPixmap], points: list[tuple[int, int]]):
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
        if event.key() == Qt.Key_Left:
            self.current_frame = max(0, self.current_frame-1)
            self.update()
        elif event.key() == Qt.Key_Right:
            self.current_frame = min(self.current_frame+1, len(self.points)-1)
            self.update()
        elif event.key() == Qt.Key_Space:
            self.hide_gui = not self.hide_gui
            self.update()
        elif event.key() == Qt.Key_Plus:
            self.scale = min(self.scale+1, 5)
            self.setFixedSize(self.frames[0].width() * self.scale, self.frames[0].height() * self.scale)
            self.update()
        elif event.key() == Qt.Key_Minus:
            self.scale = max(1, self.scale-1)
            self.setFixedSize(self.frames[0].width() * self.scale, self.frames[0].height() * self.scale)
            self.update()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        current_point = self.getScaledPoint(self.points[self.current_frame])
        drag_rect = QRect(
            current_point.x() - self.drag_margin, current_point.y() - self.drag_margin,
            self.drag_margin*2, self.drag_margin*2
        )
        if drag_rect.contains(event.pos()):
            self.dragging = True

    def mouseMoveEvent(self, event):
        if self.dragging:
            if self.current_frame in [0, len(self.frames)-1]:
                return  # ignore static point frames
            self.points[self.current_frame] = (
                int(event.pos().x() / self.scale),
                int(event.pos().y() / self.scale)
            )
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def getScaledFrame(self, frame_number) -> QPixmap:
        pixmap = self.frames[frame_number]
        scaled_pixmap = pixmap.scaled(
            int(pixmap.width() * self.scale),
            int(pixmap.height() * self.scale),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        return scaled_pixmap

    def getScaledPoint(self, point: tuple[int, int]) -> QPoint:
        scaled_point = QPoint(point[0] * self.scale, point[1] * self.scale)
        return scaled_point

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.getScaledFrame(self.current_frame))
        self.drawFrameNumber(painter)
        
        if not self.hide_gui:
            self.draw_path(painter)
            self.draw_points(painter)
    
    def drawFrameNumber(self, painter: QPainter):
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
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        last = self.getScaledPoint(self.points[0])
        for x in range(1, len(self.points)):
            current = self.getScaledPoint(self.points[x])
            painter.drawLine(last, current)
            last = current

    def draw_points(self, painter: QPainter) -> None:
        painter.setPen(QColor(0, 0, 0, 127))
        for x in range(len(self.points)):
            point = self.getScaledPoint(self.points[x])
            if x in [0, len(self.points)-1]:
                painter.setBrush(QColor(0, 255, 0, 63))
                painter.drawEllipse(point, 8, 8)
            elif x == self.current_frame:
                painter.setBrush(QColor(255, 0, 0, 127))
                painter.drawEllipse(point, self.drag_margin, self.drag_margin)
            else:
                painter.setBrush(QColor(255, 0, 0, 63))
                painter.drawEllipse(point, 8, 8)

    def get_points(self) -> list[tuple[int, int]]:
        return self.points
    
    def closeEvent(self, event):
        self.accept()
        super().closeEvent(event)
        
