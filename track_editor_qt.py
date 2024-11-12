import sys
import cv2
import threading
import time
import re
import subprocess

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QApplication, QLabel, QSlider, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QListWidget, QFileDialog, QMessageBox,
    QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import QTime, QTimer, QMutex, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QImage

# Custom modules
import storage_helper, extract_data, file_helper
import data_postprocess
import video_postprocess


class MainWindow(QtWidgets.QWidget):
    # Define a custom signal
    model_finished = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()

        # Initialize variables
        self.__INPUT_VIDEO = None
        self.__MODEL_EXE = './flytracker_app.exe'
        self.__FRAME_GAP = 10
        self.__TIMELINE_RESERVED_TEXT_WIDTH : int = 7

        self.__BACKGROUND_DARK = '#1E1E1E'
        self.__BACKGROUND_LIGHT = '#404040'
        self.__BACKGROUND_GREEN = '#306030'

        self.__AWAITING_VIDEO = True
        self.update_mutex = QMutex()

        self.update_timer_time = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frame)

        # Data variables
        self.LINKS = {}
        self.PROCESSED_DATA = None
        self.STORED_RAW_DATA = None
        self.TRIMMED_DATA = None

        # Video variables
        self.VIDEO_CAPTURE = None
        self.VIDEO_TOTAL_FRAMES = 0
        self.IS_PLAYING = False
        self.ZOOM_SCALAR = 2.2
        self.PLAYBACK_DELAY_MS = 100
        self.TRAIL_LENGTH = None

        # Constraint variables
        self.DRAW_CONSTRAINTS = True
        self.CONSTRAINTS = {'y_min': None, 'y_max': None, 'x_min': None, 'x_max': None}
        self.TIME_BOUNDS = {'start': None, 'end': None}

        # Build the UI
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Track Editor')

        # Set the background color for the entire window
        self.setStyleSheet(f"background-color: {self.__BACKGROUND_DARK};")

        # Main layout
        main_layout = QHBoxLayout(self)

        # Left frame
        self.left_frame = QtWidgets.QFrame()
        self.left_frame.setStyleSheet(f"background-color: {self.__BACKGROUND_LIGHT};")
        left_layout = QVBoxLayout(self.left_frame)

        # Preview Control Frame
        self.preview_control_frame = QtWidgets.QFrame()
        preview_control_layout = QtWidgets.QGridLayout(self.preview_control_frame)

        # Add controls to preview_control_layout (Play, Pause, Restart, Zoom, Speed, Path Length)
        controls_label = QLabel('Preview controls:')
        preview_control_layout.addWidget(controls_label, 0, 0)

        self.play_preview_button = QPushButton("Play")
        self.play_preview_button.clicked.connect(self.resume_preview)
        preview_control_layout.addWidget(self.play_preview_button, 0, 1)

        self.pause_preview_button = QPushButton("Pause")
        self.pause_preview_button.clicked.connect(self.pause_preview)
        preview_control_layout.addWidget(self.pause_preview_button, 0, 2)

        self.restart_preview_button = QPushButton("Restart")
        self.restart_preview_button.clicked.connect(self.restart_preview)
        preview_control_layout.addWidget(self.restart_preview_button, 0, 3)

        self.zoom_label = QLabel(f'Zoom level [{int(self.ZOOM_SCALAR * 100)}%]:')
        preview_control_layout.addWidget(self.zoom_label, 1, 0)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(50)
        self.zoom_slider.setMaximum(250)
        self.zoom_slider.setValue(int(self.ZOOM_SCALAR * 100))
        self.zoom_slider.valueChanged.connect(self.read_zoom_level)
        preview_control_layout.addWidget(self.zoom_slider, 1, 1, 1, 3)

        self.speed_label = QLabel(f'Playback speed [{100}%]:')
        preview_control_layout.addWidget(self.speed_label, 2, 0)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(10)
        self.speed_slider.setMaximum(200)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self.read_playback_speed)
        preview_control_layout.addWidget(self.speed_slider, 2, 1, 1, 3)

        trail_length_label = QLabel('Trail length [frames]:')
        preview_control_layout.addWidget(trail_length_label, 3, 0)

        self.trail_length_textbox = QLineEdit()
        self.trail_length_textbox.textChanged.connect(self.read_trail_length)
        preview_control_layout.addWidget(self.trail_length_textbox, 3, 1)

        spacer_item = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        preview_control_layout.addItem(spacer_item, 3, 2)
        preview_control_layout.addItem(spacer_item, 3, 3)

        left_layout.addWidget(self.preview_control_frame)
        left_layout.addSpacing(self.__FRAME_GAP)

        # FT Control Frame (Margins Frame and Model Frame)
        self.ft_control_frame = QtWidgets.QFrame()
        ft_control_layout = QHBoxLayout(self.ft_control_frame)

        # Margins Frame
        self.margins_frame = QtWidgets.QFrame()
        margins_layout = QtWidgets.QGridLayout(self.margins_frame)

        margins_ymin_label = QLabel('Top [px]:')
        margins_layout.addWidget(margins_ymin_label, 0, 0)
        self.margins_ymin_textbox = QLineEdit()
        self.margins_ymin_textbox.textChanged.connect(self.read_constraints)
        margins_layout.addWidget(self.margins_ymin_textbox, 0, 1)

        margins_ymax_label = QLabel('Bottom [px]:')
        margins_layout.addWidget(margins_ymax_label, 1, 0)
        self.margins_ymax_textbox = QLineEdit()
        self.margins_ymax_textbox.textChanged.connect(self.read_constraints)
        margins_layout.addWidget(self.margins_ymax_textbox, 1, 1)

        margins_xmin_label = QLabel('Left [px]:')
        margins_layout.addWidget(margins_xmin_label, 2, 0)
        self.margins_xmin_textbox = QLineEdit()
        self.margins_xmin_textbox.textChanged.connect(self.read_constraints)
        margins_layout.addWidget(self.margins_xmin_textbox, 2, 1)

        margins_xmax_label = QLabel('Right [px]:')
        margins_layout.addWidget(margins_xmax_label, 3, 0)
        self.margins_xmax_textbox = QLineEdit()
        self.margins_xmax_textbox.textChanged.connect(self.read_constraints)
        margins_layout.addWidget(self.margins_xmax_textbox, 3, 1)

        start_frame_label = QLabel('Start frame:')
        margins_layout.addWidget(start_frame_label, 4, 0)
        self.start_frame_textbox = QLineEdit()
        self.start_frame_textbox.textChanged.connect(self.read_time_bounds)
        margins_layout.addWidget(self.start_frame_textbox, 4, 1)

        end_frame_label = QLabel('End frame:')
        margins_layout.addWidget(end_frame_label, 5, 0)
        self.end_frame_textbox = QLineEdit()
        self.end_frame_textbox.textChanged.connect(self.read_time_bounds)
        margins_layout.addWidget(self.end_frame_textbox, 5, 1)

        self.margins_view_checkbox = QtWidgets.QCheckBox("Show\nConstraints")
        self.margins_view_checkbox.setChecked(True)
        self.margins_view_checkbox.stateChanged.connect(self.toggle_constraints)
        margins_layout.addWidget(self.margins_view_checkbox, 6, 0)

        self.apply_constraints_button = QPushButton("Apply\nConstraints")
        self.apply_constraints_button.clicked.connect(self.apply_constraints)
        margins_layout.addWidget(self.apply_constraints_button, 6, 1)

        ft_control_layout.addWidget(self.margins_frame)

        # Model Frame
        self.model_frame = QtWidgets.QFrame()
        model_layout = QtWidgets.QGridLayout(self.model_frame)

        model_start_frame_label = QLabel('Start frame:')
        model_layout.addWidget(model_start_frame_label, 0, 0)
        self.model_start_frame_textbox = QLineEdit()
        model_layout.addWidget(self.model_start_frame_textbox, 0, 1)

        model_end_frame_label = QLabel('End frame:')
        model_layout.addWidget(model_end_frame_label, 1, 0)
        self.model_end_frame_textbox = QLineEdit()
        model_layout.addWidget(self.model_end_frame_textbox, 1, 1)

        self.model_run_button = QPushButton("Run Model")
        self.model_run_button.clicked.connect(self.run_model_wrapper)
        model_layout.addWidget(self.model_run_button, 2, 0, 1, 2)

        ft_control_layout.addWidget(self.model_frame)

        left_layout.addWidget(self.ft_control_frame)
        left_layout.addSpacing(self.__FRAME_GAP)

        # Data Control Frame (Links Control Frame and Export IDs Frame)
        self.data_control_frame = QtWidgets.QFrame()
        data_control_layout = QHBoxLayout(self.data_control_frame)

        # Links Control Frame
        self.links_control_frame = QtWidgets.QFrame()
        links_layout = QtWidgets.QGridLayout(self.links_control_frame)

        links_label = QLabel('Links:')
        links_layout.addWidget(links_label, 0, 0)

        self.list_add_button = QPushButton("Add")
        self.list_add_button.clicked.connect(self.list_links_add)
        links_layout.addWidget(self.list_add_button, 0, 1)

        self.list_edt_button = QPushButton("Edit")
        self.list_edt_button.clicked.connect(self.list_links_edit)
        links_layout.addWidget(self.list_edt_button, 0, 2)

        self.list_del_button = QPushButton("Remove")
        self.list_del_button.clicked.connect(self.list_links_delete)
        links_layout.addWidget(self.list_del_button, 0, 3)

        self.links_listbox = QListWidget()
        links_layout.addWidget(self.links_listbox, 1, 0, 1, 4)

        gap_label = QLabel('Gap threshold [px]:')
        links_layout.addWidget(gap_label, 2, 0, 1, 2)
        self.gap_textbox = QLineEdit()
        links_layout.addWidget(self.gap_textbox, 2, 2, 1, 2)

        self.auto_button = QPushButton("Automatically Find Links")
        self.auto_button.clicked.connect(self.auto_process)
        links_layout.addWidget(self.auto_button, 3, 0, 1, 4)

        data_control_layout.addWidget(self.links_control_frame)

        # Export IDs Frame
        self.export_ids_frame = QtWidgets.QFrame()
        export_ids_layout = QtWidgets.QGridLayout(self.export_ids_frame)

        export_list_label = QLabel('Export IDs:')
        export_ids_layout.addWidget(export_list_label, 0, 0, 1, 2)

        self.export_listbox = QListWidget()
        export_ids_layout.addWidget(self.export_listbox, 1, 0, 1, 2)

        self.export_list_add_button = QPushButton("Add")
        self.export_list_add_button.clicked.connect(self.list_export_add)
        export_ids_layout.addWidget(self.export_list_add_button, 2, 0)

        self.export_list_del_button = QPushButton("Remove")
        self.export_list_del_button.clicked.connect(self.list_export_delete)
        export_ids_layout.addWidget(self.export_list_del_button, 2, 1)

        data_control_layout.addWidget(self.export_ids_frame)

        left_layout.addWidget(self.data_control_frame)
        left_layout.addSpacing(self.__FRAME_GAP)

        # External Frame (Import and Export Buttons)
        self.external_frame = QtWidgets.QFrame()
        external_layout = QHBoxLayout(self.external_frame)

        # Import Buttons Frame
        self.import_buttons_frame = QtWidgets.QFrame()
        import_buttons_layout = QHBoxLayout(self.import_buttons_frame)

        self.import_avi_button = QPushButton("Import Video")
        self.import_avi_button.clicked.connect(self.import_video)
        import_buttons_layout.addWidget(self.import_avi_button)

        self.reset_app_button = QPushButton("Reset")
        self.reset_app_button.clicked.connect(self.reset_app)
        import_buttons_layout.addWidget(self.reset_app_button)

        external_layout.addWidget(self.import_buttons_frame)

        # Export Buttons Frame
        self.export_buttons_frame = QtWidgets.QFrame()
        export_buttons_layout = QHBoxLayout(self.export_buttons_frame)

        self.export_csv_button = QPushButton("Export to CSV")
        self.export_csv_button.clicked.connect(self.export_csv)
        export_buttons_layout.addWidget(self.export_csv_button)

        self.export_mp4_button = QPushButton("Export to MP4")
        self.export_mp4_button.clicked.connect(self.export_mp4)
        export_buttons_layout.addWidget(self.export_mp4_button)

        external_layout.addWidget(self.export_buttons_frame)

        left_layout.addWidget(self.external_frame)

        # Right frame
        self.right_frame = QtWidgets.QFrame()
        self.right_frame.setStyleSheet(f"background-color: {self.__BACKGROUND_DARK};")
        right_layout = QVBoxLayout(self.right_frame)

        # Preview Panel
        self.preview_panel = QLabel()
        self.preview_panel.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.preview_panel)

        # Timeline Slider
        timeline_frame = QtWidgets.QFrame()
        timeline_layout = QHBoxLayout(timeline_frame)

        self.timeline_label = QLabel(f'[{0:^{self.__TIMELINE_RESERVED_TEXT_WIDTH}}]')
        timeline_layout.addWidget(self.timeline_label)

        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(self.VIDEO_TOTAL_FRAMES)
        self.timeline_slider.valueChanged.connect(self.read_timeline_value)
        timeline_layout.addWidget(self.timeline_slider)

        right_layout.addWidget(timeline_frame)

        # Add frames to main layout
        main_layout.addWidget(self.left_frame)
        main_layout.addWidget(self.right_frame)

        # Disable elements until video is loaded
        self.toggle_all_panels(False)

        # Connect the custom signal to the slot
        self.model_finished.connect(self.on_model_finished)

    def toggle_panel(self, widget, state):
        widget.setEnabled(state)

    def toggle_all_panels(self, state):
        self.toggle_panel(self.right_frame, state)
        self.toggle_panel(self.preview_control_frame, state)
        self.toggle_panel(self.margins_frame, state)
        self.toggle_panel(self.model_frame, state)
        self.toggle_panel(self.data_control_frame, state)
        self.toggle_panel(self.export_buttons_frame, state)

    def get_textbox_value(self, textbox):
        try:
            return int(textbox.text())
        except ValueError:
            return None

    def set_textbox_value(self, textbox, value):
        textbox.setText(str(value))

    def import_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select a Video File", "", "Video files (*.avi);;All files (*.*)"
        )
        if file_path != '':
            if not self.__AWAITING_VIDEO:
                self.update_timer.stop()
            
            old_path = self.__INPUT_VIDEO
            self.__INPUT_VIDEO = file_path
            try:
                self.await_file_opened()
                self.reset_app()
            except Exception as err:
                QMessageBox.warning(self, 'Error', f'An exception occurred in await_file_opened():\n{err}')
                self.__INPUT_VIDEO = old_path

                if not self.__AWAITING_VIDEO:
                    self.update_timer.start()

    def await_file_opened(self):
        if self.__INPUT_VIDEO is not None:
            # Read raw data from csv file
            raw_file = storage_helper.find_raw_data(self.__INPUT_VIDEO)
            self.STORED_RAW_DATA = storage_helper.read_from_csv(raw_file) if raw_file is not None else None

            if self.VIDEO_CAPTURE is not None:
                self.VIDEO_CAPTURE.release()
            
            # Initialize the video capture
            self.VIDEO_CAPTURE = cv2.VideoCapture(self.__INPUT_VIDEO)
            self.VIDEO_TOTAL_FRAMES = int(self.VIDEO_CAPTURE.get(cv2.CAP_PROP_FRAME_COUNT))
            self.PLAYBACK_DELAY_MS = int(1000 / self.VIDEO_CAPTURE.get(cv2.CAP_PROP_FPS))

            if self.STORED_RAW_DATA is not None:
                self.init_for_video()
                return
            else:
                self.init_for_model()
                return

    def init_for_video(self):
        # Enable elements after a video has loaded
        self.toggle_all_panels(True)

        # Set default trail length
        self.set_textbox_value(self.trail_length_textbox, '-1')

        # Adjust the timeline bounds
        self.timeline_slider.setMaximum(self.VIDEO_TOTAL_FRAMES)

        # Adjust time bounds for the model
        self.set_textbox_value(self.model_start_frame_textbox, '0')
        self.set_textbox_value(self.model_end_frame_textbox, str(self.VIDEO_TOTAL_FRAMES))

        # Adjust time bounds for export
        self.set_textbox_value(self.start_frame_textbox, '0')
        self.set_textbox_value(self.end_frame_textbox, str(self.VIDEO_TOTAL_FRAMES))
        self.read_time_bounds()

        # Set default margins for the constraints
        self.set_textbox_value(self.margins_xmin_textbox, '0')
        self.set_textbox_value(self.margins_xmax_textbox, '0')
        self.set_textbox_value(self.margins_ymin_textbox, '0')
        self.set_textbox_value(self.margins_ymax_textbox, '0')
        self.read_constraints()

        self.__AWAITING_VIDEO = False

        # Allow preview playback to start
        self.IS_PLAYING = True

    def init_for_model(self):
        self.__AWAITING_VIDEO = True

        # Enable Model Launch Components, Disable the rest
        self.toggle_all_panels(False)
        self.toggle_panel(self.model_frame, True)

        # Set default trail length
        self.set_textbox_value(self.trail_length_textbox, '-1')

        # Adjust time bounds for the model
        self.set_textbox_value(self.model_start_frame_textbox, '0')
        self.set_textbox_value(self.model_end_frame_textbox, str(self.VIDEO_TOTAL_FRAMES))

        # Emphasize the 'Model Launch Components' frame
        self.model_frame.setStyleSheet(f'background-color: {self.__BACKGROUND_GREEN}; border-radius: 15px;')

    def update_frame(self):
        if not self.update_mutex.tryLock():
            return  # Exit if the mutex is already locked (another instance is running)

        self.update_timer_time = QTime.currentTime()

        try:
            self.read_timeline_value()

            if self.IS_PLAYING:
                ret, frame = self.VIDEO_CAPTURE.read()
                if not ret:  # restart video once reached end
                    self.VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.VIDEO_CAPTURE.read()
            else:
                self.VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, self.VIDEO_CAPTURE.get(cv2.CAP_PROP_POS_FRAMES) - 1)
                ret, frame = self.VIDEO_CAPTURE.read()

            # Update timeline position
            frame_number = int(self.VIDEO_CAPTURE.get(cv2.CAP_PROP_POS_FRAMES) - 1)
            self.timeline_slider.blockSignals(True)
            self.timeline_slider.setValue(frame_number)
            self.timeline_slider.blockSignals(False)

            # Generate next frame
            start_frame = 0 if self.TRAIL_LENGTH is None else max(0, frame_number - self.TRAIL_LENGTH)
            fly_paths = video_postprocess.construct_paths(self.TRIMMED_DATA, frame_number, paths=None, start_frame=start_frame)
            adjusted_frame = video_postprocess.copy_frame(frame)
            video_postprocess.draw_paths_onto_frame(self.TRIMMED_DATA[frame_number], adjusted_frame, fly_paths)

            if self.DRAW_CONSTRAINTS:
                video_postprocess.draw_constraints_onto_frame(adjusted_frame, self.CONSTRAINTS)

            # Place adjusted and original frames side by side
            height, width, _ = frame.shape
            if width < height:
                merged_frame = cv2.hconcat([adjusted_frame, frame])
            else:
                merged_frame = cv2.vconcat([adjusted_frame, frame])

            # Convert the frame to a format that can be used by Qt
            rgb_image = cv2.cvtColor(merged_frame, cv2.COLOR_BGR2RGB)
            height, width, _ = rgb_image.shape
            bytes_per_line = 3 * width
            q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)

            # Scale the frame
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                int(pixmap.width() * self.ZOOM_SCALAR),
                int(pixmap.height() * self.ZOOM_SCALAR),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # Draw the frame onto the preview panel
            self.preview_panel.setPixmap(scaled_pixmap)

        except Exception as err:
            # Stop the timer to prevent further calls
            self.update_timer.stop()
            # Show error message
            QMessageBox.warning(self, 'Error', f'An exception occurred in update_frame():\n{err}')
        else:
            # Schedule next update only if no exception occurred
            elapsed_time = self.update_timer_time.msecsTo(QTime.currentTime())
            self.update_timer.start(max(0, self.PLAYBACK_DELAY_MS - elapsed_time))
        finally:
            # Always release the mutex
            self.update_mutex.unlock()

    def read_zoom_level(self):
        self.ZOOM_SCALAR = self.zoom_slider.value() / 100
        self.zoom_label.setText(f'Zoom level [{self.zoom_slider.value()}%]:')

    def read_playback_speed(self):
        speed_factor = self.speed_slider.value() / 100
        self.speed_label.setText(f'Playback speed [{self.speed_slider.value()}%]:')
        if self.VIDEO_CAPTURE:
            fps = self.VIDEO_CAPTURE.get(cv2.CAP_PROP_FPS)
            self.PLAYBACK_DELAY_MS = int(1000 / (fps * speed_factor))

    def read_timeline_value(self):
        self.timeline_label.setText(f'[{self.timeline_slider.value():^{self.__TIMELINE_RESERVED_TEXT_WIDTH}}]')
        if self.VIDEO_CAPTURE:
            timeline_pos = int(self.timeline_slider.value())
            current_frame = int(self.VIDEO_CAPTURE.get(cv2.CAP_PROP_POS_FRAMES) - 1)
            if timeline_pos != current_frame:
                self.VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, timeline_pos)

    def read_trail_length(self):
        self.TRAIL_LENGTH = self.get_textbox_value(self.trail_length_textbox)
        if self.TRAIL_LENGTH is None or self.TRAIL_LENGTH < 0:
            self.TRAIL_LENGTH = None

    def resume_preview(self):
        self.IS_PLAYING = True

    def pause_preview(self):
        self.IS_PLAYING = False

    def restart_preview(self):
        if self.VIDEO_CAPTURE:
            self.VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.timeline_slider.setValue(0)

    def reset_variables(self):
        self.LINKS = {}
        
        self.ZOOM_SCALAR = 2.2
        self.PLAYBACK_DELAY_MS = 100 if self.VIDEO_CAPTURE is None else int(1000 / self.VIDEO_CAPTURE.get(cv2.CAP_PROP_FPS))
        self.TRAIL_LENGTH = None

        self.VIDEO_TOTAL_FRAMES = 0 if self.VIDEO_CAPTURE is None else int(self.VIDEO_CAPTURE.get(cv2.CAP_PROP_FRAME_COUNT))

        if self.VIDEO_CAPTURE is not None:
            self.VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self.DRAW_CONSTRAINTS = True
        self.TIME_BOUNDS = {'start': None, 'end': None}
    
    def reset_gui_components(self):
        self.zoom_slider.setValue(int(self.ZOOM_SCALAR * 100))
        self.speed_slider.setValue(100)
        self.set_textbox_value(self.trail_length_textbox, '-1')

        self.timeline_slider.setValue(0)
        self.timeline_slider.setMaximum(self.VIDEO_TOTAL_FRAMES)

        self.preview_panel.clear()

        self.set_textbox_value(self.model_start_frame_textbox, '0')
        self.set_textbox_value(self.model_end_frame_textbox, str(self.VIDEO_TOTAL_FRAMES))

        self.set_textbox_value(self.start_frame_textbox, '0')
        self.set_textbox_value(self.end_frame_textbox, str(self.VIDEO_TOTAL_FRAMES))

        self.set_textbox_value(self.gap_textbox, '3')
        
        self.list_links_reset()
        self.list_export_reset()

    def reset_app(self):
        if not self.__AWAITING_VIDEO:
            self.update_timer.stop()

        self.reset_variables()
        self.reset_gui_components()

        # Remove emphasis from 'Model Launch Components' frame
        if not self.__AWAITING_VIDEO:
            self.model_frame.setStyleSheet(f'')

        if not self.__AWAITING_VIDEO:
            # Process the loaded data automatically
            self.auto_process()
            self.update_timer.start()

    def list_export_reset(self):
        self.export_listbox.clear()

    def list_export_add(self):
        ans, ok = QtWidgets.QInputDialog.getText(
            self, 
            "Input", 
            "Enter IDs for export:", 
            QtWidgets.QLineEdit.Normal, 
            '', 
            flags=QtCore.Qt.WindowFlags(QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)
        )
        if ok and ans:
            ids = re.findall(r'\d+', ans)
            for id in ids:
                self.export_listbox.addItem(id)

    def list_export_delete(self):
        selected_items = self.export_listbox.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.export_listbox.takeItem(self.export_listbox.row(item))

    def list_links_add(self):
        ans, ok = QtWidgets.QInputDialog.getText(
            self, 
            "Input", 
            "Enter 2 IDs to merge:", 
            QtWidgets.QLineEdit.Normal, 
            '', 
            flags=QtCore.Qt.WindowFlags(QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint)
        )
        if ok and ans:
            ids = [int(num) for num in re.findall(r'\d+', ans)]
            if len(ids) >= 2:
                swapped, actual = max(ids), min(ids)
                self.LINKS[swapped] = actual
                self.process_data()

    def list_links_edit(self):
        selected_items = self.links_listbox.selectedItems()
        if not selected_items:
            return
        current_value = selected_items[0].text()
        swapped, actual = current_value.replace('->', ' ').split()
        swapped, actual = int(swapped), int(actual)
        ans, ok = QtWidgets.QInputDialog.getText(self, "Input", "Enter 2 IDs to merge:", text=f"{swapped} {actual}")
        if ok and ans:
            ids = [int(num) for num in re.findall(r'\d+', ans)]
            if len(ids) >= 2:
                del self.LINKS[swapped]
                swapped, actual = max(ids), min(ids)
                self.LINKS[swapped] = actual
                self.process_data()

    def list_links_delete(self):
        selected_items = self.links_listbox.selectedItems()
        if not selected_items:
            return
        current_value = selected_items[0].text()
        swapped, actual = current_value.replace('->', ' ').split()
        swapped = int(swapped)
        del self.LINKS[swapped]
        self.process_data()
    
    def list_links_reset(self):
        self.links_listbox.clear()

    def process_data(self):
        self.populate_links()
        self.PROCESSED_DATA = data_postprocess.process_data(self.STORED_RAW_DATA, self.LINKS)
        self.apply_constraints()

    def populate_links(self):
        self.list_links_reset()
        for swapped, actual in self.LINKS.items():
            self.links_listbox.addItem(f'{swapped:<5}->{actual:>5}')

    def auto_process(self):
        gap = self.get_textbox_value(self.gap_textbox)
        if gap is None:
            gap = 3
            self.set_textbox_value(self.gap_textbox, gap)
        
        self.LINKS = data_postprocess.generate_links(self.STORED_RAW_DATA, gap)
        self.process_data()

    def apply_constraints(self):
        self.read_constraints()
        self.read_time_bounds()
        self.TRIMMED_DATA = data_postprocess.apply_constraints(self.PROCESSED_DATA, self.CONSTRAINTS)
        self.TRIMMED_DATA = {k: v if self.TIME_BOUNDS['start'] <= k < self.TIME_BOUNDS['end'] else [] for k, v in self.TRIMMED_DATA.items()}

    def toggle_constraints(self):
        self.DRAW_CONSTRAINTS = not self.DRAW_CONSTRAINTS

    def read_constraints(self):
        if not self.VIDEO_CAPTURE:
            return

        # get video dimensions
        width = int(self.VIDEO_CAPTURE.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.VIDEO_CAPTURE.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # try reading values
        x_min = self.get_textbox_value(self.margins_xmin_textbox)
        x_max = self.get_textbox_value(self.margins_xmax_textbox)
        y_min = self.get_textbox_value(self.margins_ymin_textbox)
        y_max = self.get_textbox_value(self.margins_ymax_textbox)

        # replace failed values
        x_min = x_min if x_min is not None else 0
        x_max = x_max if x_max is not None else 0
        y_min = y_min if y_min is not None else 0
        y_max = y_max if y_max is not None else 0

        # clamp results of converting margins to actual constraints
        self.CONSTRAINTS['x_min'] = data_postprocess.clamp(x_min, 0, width - 1)
        self.CONSTRAINTS['x_max'] = data_postprocess.clamp(width - x_max - 1, 0, width - 1)
        self.CONSTRAINTS['y_min'] = data_postprocess.clamp(y_min, 0, height - 1)
        self.CONSTRAINTS['y_max'] = data_postprocess.clamp(height - y_max - 1, 0, height - 1)

        # invert constraints if they got inverted by large margins (safeguard for user error)
        if self.CONSTRAINTS['x_max'] < self.CONSTRAINTS['x_min']:
            self.CONSTRAINTS['x_max'], self.CONSTRAINTS['x_min'] = self.CONSTRAINTS['x_min'], self.CONSTRAINTS['x_max']
        if self.CONSTRAINTS['y_max'] < self.CONSTRAINTS['y_min']:
            self.CONSTRAINTS['y_max'], self.CONSTRAINTS['y_min'] = self.CONSTRAINTS['y_min'], self.CONSTRAINTS['y_max']

    def read_time_bounds(self):
        # try reading values
        start = self.get_textbox_value(self.start_frame_textbox)
        end = self.get_textbox_value(self.end_frame_textbox)

        # replace failed values
        start = start if start is not None else 0
        end = end if end is not None else self.VIDEO_TOTAL_FRAMES

        # clamp bounds to actual video bounds
        start = data_postprocess.clamp(start, 0, self.VIDEO_TOTAL_FRAMES)
        end = data_postprocess.clamp(end, 0, self.VIDEO_TOTAL_FRAMES)

        # swap bounds if they are inverted (safeguard for user error)
        if end < start:
            start, end = end, start

        # apply values
        self.TIME_BOUNDS['start'] = start
        self.TIME_BOUNDS['end'] = end

    def get_export_ids(self):
        collapsed_links = data_postprocess.propagate_links(self.LINKS)
        requested_ids = set(int(self.export_listbox.item(i).text()) for i in range(self.export_listbox.count()))
        for id in requested_ids:
            if id not in collapsed_links:
                collapsed_links[id] = id
        return set(collapsed_links[id] for id in requested_ids)

    def export_csv(self):
        # Prepare output basename
        output_path = storage_helper.get_prepared_path(self.__INPUT_VIDEO)
        try:
            storage_helper.write_to_csv(self.TRIMMED_DATA, f'{output_path}_result.csv')
            QMessageBox.information(self, 'Success', f'Exported file to:\n{output_path}_result.csv')
            try:
                p = extract_data.extract_findings(f'{output_path}_result.csv', self.get_export_ids())
                QMessageBox.information(self, 'Success', f'Extracted data points to:\n{p}')
            except Exception as e:
                QMessageBox.warning(self, 'Error', f'Failed to extract data points!\n{str(e)}')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to export CSV file!\n{str(e)}')

    def export_mp4(self):
        output_path = storage_helper.get_prepared_path(self.__INPUT_VIDEO)
        try:
            requested_data = data_postprocess.filter_by_ids(self.TRIMMED_DATA, self.get_export_ids())
            video_postprocess.annotate_video(requested_data, self.__INPUT_VIDEO, f'{output_path}_result.mp4', None, False)
            QMessageBox.information(self, 'Success', f'Exported file to:\n{output_path}_result.mp4')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to export MP4 file!\n{str(e)}')

    def run_model_wrapper(self):
        # Get start and end frames from textboxes
        try:
            start_frame = int(self.get_textbox_value(self.model_start_frame_textbox))
            end_frame   = int(self.get_textbox_value(self.model_end_frame_textbox))
        except:
            QMessageBox.warning(self, 'Error', 'Please provide valid inputs,\nbot `start frame` and `end frame` must be numeric values.')
            return

        # Verify start and end times
        if end_frame < start_frame:
            QMessageBox.warning(self, 'Error', 'Please provide valid inputs,\n`start frame` cannot be greater than `end frame`.')
            return
        if start_frame < 0 or end_frame < 0:
            QMessageBox.warning(self, 'Error', 'Please provide valid inputs,\nneither `start frame` nor `end frame` can be negative values.')
            return

        # Remove emphasis from 'Model Launch Components' frame
        self.model_frame.setStyleSheet('')

        # Disable the model_frame to prevent running more than once at a time
        self.toggle_panel(self.model_frame, False)

        # Ensure that the model executable is present
        if not file_helper.check_existance(self.__MODEL_EXE):
            QMessageBox.warning(self, 'Error', f'The vision model executable is missing at `{self.__MODEL_EXE}`.')
            return

        # Run the model on a separate thread
        threading.Thread(target=self.run_model, args=(self.__INPUT_VIDEO, start_frame, end_frame)).start()

    def run_model(self, input_path, start_frame, end_frame):
        start_time = time.time()
        model_process = subprocess.Popen(
            [self.__MODEL_EXE, input_path, str(start_frame), str(end_frame)],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        model_process.wait()
        elapsed_time = time.time() - start_time

        # Notify the user about the completion via the signal
        formatted_time = time.strftime('%M:%S', time.gmtime(elapsed_time))

        # Emit the signal to notify the main thread
        self.model_finished.emit((model_process.returncode == 0), formatted_time)
        
    def on_model_finished(self, success, elapsed_time_str):
        if success:
            QMessageBox.information(self, 'Success', f'Analysis Complete!\nElapsed Time: {elapsed_time_str}')
        else:
            QMessageBox.warning(self, 'Error', f'Analysis Failed!\nElapsed Time: {elapsed_time_str}')
            return

        self.await_file_opened()

    def get_frames(self, start_frame: int, frames_count: int) -> list[QPixmap]:
        frames = []
        paused_at = self.VIDEO_CAPTURE.get(cv2.CAP_PROP_POS_FRAMES)
        self.VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        try:
            for _ in range(start_frame, start_frame + frames_count + 1):
                ret, frame = self.VIDEO_CAPTURE.read()

                # Convert the frame to a format that can be used by Qt
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, _ = rgb_image.shape
                bytes_per_line = 3 * width
                q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)

                # Scale the frame
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaled(
                    int(pixmap.width() * self.ZOOM_SCALAR),
                    int(pixmap.height() * self.ZOOM_SCALAR),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                # Append the requested frame
                frames.append(scaled_pixmap)
        except Exception as error:
            QMessageBox.warning(self, 'Error', 'The video capture object failed to retrive the requested frames.')
            frames = []
        finally:
            # Revert timeline progress on the video capture object
            self.VIDEO_CAPTURE.set(cv2.CAP_PROP_POS_FRAMES, paused_at)
            return frames

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setFont(QFont('Consolas', 12))
    app.setStyleSheet("""
        QWidget:enabled { color: white; }

        QLineEdit, QTextEdit, QListWidget {
            border: 1px solid #999999;
            border-radius: 5px;
            padding: 15px;
        }

        QPushButton {
            border: 2px solid #669966;
            border-radius: 8px;
        }

        QPushButton:pressed {
            border: 2px solid #388E3C;
        }

        QSlider::handle:hover {
            background: #60EE60;
        }
        
        QSlider::handle:pressed {
            background: #388E3C;
        }

        QCheckBox::indicator {
            border-radius: 8px;
            width: 18px;
            height: 18px;
        }

        QCheckBox::indicator:checked {
            background-color: #669966;
            border: 1px solid #388E3C;
        }

        QCheckBox::indicator:unchecked {
            background-color: transparent;
            border: 1px solid #999999;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
