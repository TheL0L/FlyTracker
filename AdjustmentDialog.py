from PyQt5.QtWidgets import QDialog
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QPoint, QRect


class AdjustmentDialog(QDialog):
    def __init__(self, frames: list[QPixmap], points: list[tuple[int, int]]):
        super().__init__()

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle("Manual Path Adjustment")
        self.setFixedSize(frames[0].width(), frames[0].height())

        self.frames = frames
        self.points = points

        self.current_frame = 1
        self.dragging = False
        self.drag_margin = 15
        self.hide_gui = False

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
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        current_point = QPoint(self.points[self.current_frame][0], self.points[self.current_frame][1])
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
            self.points[self.current_frame] = (event.pos().x(), event.pos().y())
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.frames[self.current_frame])
        
        if not self.hide_gui:
            self.draw_path(painter)
            self.draw_points(painter)

    def draw_path(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        last = QPoint(self.points[0][0], self.points[0][1])
        for x in range(1, len(self.points)):
            current = QPoint(self.points[x][0], self.points[x][1])
            painter.drawLine(last, current)
            last = current

    def draw_points(self, painter: QPainter) -> None:
        painter.setPen(QPen())
        for x in range(len(self.points)):
            point = QPoint(self.points[x][0], self.points[x][1])
            if x in [0, len(self.points)-1]:
                painter.setBrush(QColor(0, 255, 0, 20))
                painter.drawEllipse(point, 5, 5)
            elif x == self.current_frame:
                painter.setBrush(QColor(255, 0, 0, 127))
                painter.drawEllipse(point, self.drag_margin, self.drag_margin)
            else:
                painter.setBrush(QColor(255, 0, 0, 20))
                painter.drawEllipse(point, 5, 5)

    def get_points(self) -> list[tuple[int, int]]:
        return self.points
    
    def closeEvent(self, event):
        self.accept()
        super().closeEvent(event)
        
