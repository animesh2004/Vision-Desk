import sys
import os
import cv2
import numpy as np
import time
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QSlider, 
                             QCheckBox, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QComboBox, QFileDialog, QMessageBox, QTabWidget, QStatusBar,
                             QSpinBox, QStyle, QSplitter, QLCDNumber)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon, QFont, QPalette, QColor


class ROISelector:
    """Class to handle ROI selection on camera feed"""
    
    def __init__(self):
        self.selecting = False
        self.selected = False
        self.start_point = (0, 0)
        self.end_point = (0, 0)
        self.roi = None
    
    def start_selection(self, x, y):
        self.selecting = True
        self.selected = False
        self.start_point = (x, y)
        self.end_point = (x, y)
    
    def update_selection(self, x, y):
        if self.selecting:
            self.end_point = (x, y)
    
    def finish_selection(self):
        if self.selecting:
            self.selecting = False
            self.selected = True
            
            # Ensure start_point is top-left and end_point is bottom-right
            x1, y1 = min(self.start_point[0], self.end_point[0]), min(self.start_point[1], self.end_point[1])
            x2, y2 = max(self.start_point[0], self.end_point[0]), max(self.start_point[1], self.end_point[1])
            
            # Ensure minimum size of ROI
            if x2 - x1 < 10 or y2 - y1 < 10:
                self.selected = False
                self.roi = None
                return
                
            self.roi = (x1, y1, x2, y2)
    
    def clear_selection(self):
        self.selecting = False
        self.selected = False
        self.roi = None
    
    def get_roi(self):
        if self.selected:
            return self.roi
        return None
    
    def draw_roi(self, frame):
        if self.selecting or self.selected:
            x1 = min(self.start_point[0], self.end_point[0])
            y1 = min(self.start_point[1], self.end_point[1])
            x2 = max(self.start_point[0], self.end_point[0])
            y2 = max(self.start_point[1], self.end_point[1])
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw dimensions text
            text = f"{x2-x1}x{y2-y1}"
            cv2.putText(frame, text, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return frame


class VideoRecorder:
    """Class to handle video recording"""
    
    def __init__(self, fps=30.0):
        self.output = None
        self.is_recording = False
        self.fps = fps
        self.filename = None
        self.start_time = None
        self.frame_size = None
    
    def start_recording(self, frame_size):
        if self.is_recording:
            return
            
        # Create output directory if it doesn't exist
        os.makedirs('recordings', exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = f"recordings/visiondesk_{timestamp}.avi"
        
        # Initialize VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.output = cv2.VideoWriter(self.filename, fourcc, self.fps, frame_size)
        self.frame_size = frame_size
        self.is_recording = True
        self.start_time = time.time()
        return self.filename
    
    def write_frame(self, frame):
        if self.is_recording and self.output and frame is not None:
            # Ensure frame size matches what was specified
            h, w = frame.shape[:2]
            if (w, h) != self.frame_size:
                frame = cv2.resize(frame, self.frame_size)
            self.output.write(frame)
    
    def stop_recording(self):
        if self.is_recording and self.output:
            self.output.release()
            self.is_recording = False
            return self.filename
        return None
    
    def get_recording_time(self):
        if self.is_recording and self.start_time:
            return int(time.time() - self.start_time)
        return 0


class VideoWidget(QLabel):
    """Custom widget to display and interact with camera feed"""
    
    roi_selected = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.roi_selector = ROISelector()
        self.setMouseTracking(True)
        self.setStyleSheet("border: 1px solid #444; background-color: #222;")
        self.setMinimumSize(640, 480)
        self.drag_start_pos = None
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            # Convert position from Qt coordinates to image coordinates
            img_coords = self.widget_to_image_coords(pos.x(), pos.y())
            if img_coords:
                img_x, img_y = img_coords
                self.roi_selector.start_selection(img_x, img_y)
                self.drag_start_pos = pos
    
    def mouseMoveEvent(self, event):
        if self.roi_selector.selecting and self.drag_start_pos:
            pos = event.pos()
            # Convert position from Qt coordinates to image coordinates
            img_coords = self.widget_to_image_coords(pos.x(), pos.y())
            if img_coords:
                img_x, img_y = img_coords
                self.roi_selector.update_selection(img_x, img_y)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.roi_selector.selecting:
            self.roi_selector.finish_selection()
            if self.roi_selector.selected:
                self.roi_selected.emit()
            self.drag_start_pos = None
    
    def widget_to_image_coords(self, widget_x, widget_y):
        """Convert widget coordinates to image coordinates"""
        if not self.pixmap() or self.pixmap().isNull():
            return None
            
        # Get the scaled dimensions
        img_rect = self.pixmap().rect()
        scaled_rect = self.rect()
        
        # Calculate scaling factors
        scale_x = img_rect.width() / scaled_rect.width()
        scale_y = img_rect.height() / scaled_rect.height()
        
        # Calculate offset if image is centered in the widget
        offset_x = (scaled_rect.width() - img_rect.width() / scale_x) / 2
        offset_y = (scaled_rect.height() - img_rect.height() / scale_y) / 2
        
        # Adjust coordinates
        img_x = int((widget_x - offset_x) * scale_x)
        img_y = int((widget_y - offset_y) * scale_y)
        
        # Ensure coordinates are within image bounds
        img_x = max(0, min(img_x, img_rect.width() - 1))
        img_y = max(0, min(img_y, img_rect.height() - 1))
        
        return img_x, img_y


class FPSCounter:
    """Class to calculate and display frames per second"""
    
    def __init__(self, update_interval=1.0):
        self.frame_count = 0
        self.fps = 0
        self.last_update_time = time.time()
        self.update_interval = update_interval
    
    def update(self):
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        
        if elapsed > self.update_interval:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_update_time = current_time
            
        return self.fps


class VisionDesk(QMainWindow):
    """Main application window for VisionDesk"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('VisionDesk | Advanced Computer Vision')
        
        # Set app icon
        app_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.setWindowIcon(app_icon)
        
        # Apply dark theme
        self.apply_dark_theme()
        
        # Initialize UI components
        self.initUI()
        
        # Initialize camera
        self.camera = None
        self.camera_index = 0
        self.open_camera()
        
        # Initialize variables
        self.use_canny = False
        self.low_threshold = 50
        self.high_threshold = 150
        self.current_filter = "None"
        self.snapshot_counter = 0
        self.pause_video = False
        
        # Create a video recorder instance
        self.recorder = VideoRecorder()
        
        # Create an FPS counter
        self.fps_counter = FPSCounter()
        
        # Initialize face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.detect_faces = False
        
        # Set up timer for updating the camera feed
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update every 30ms (~33 fps)
        
        # Load most recent frame
        self.current_frame = None
        
        # Status message timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.clear_status)
        
        # Position window in center of screen
        self.center_window()
    
    def apply_dark_theme(self):
        """Apply dark theme to application"""
        dark_palette = QPalette()
        
        # Set colors
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        # Apply the palette
        self.setPalette(dark_palette)
        
        # Additional stylesheet for fine-tuning
        self.setStyleSheet("""
            QWidget {
                background-color: #353535;
                color: #ffffff;
                font-family: Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #555555;
                border: 1px solid #777;
                border-radius: 4px;
                padding: 5px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #666666;
                border: 1px solid #888;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #777777;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #444444;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #999999;
                border: 1px solid #777777;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QComboBox {
                border: 1px solid #555;
                border-radius: 3px;
                padding: 1px 18px 1px 3px;
                min-width: 6em;
                background-color: #444;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                top: -1px;
            }
            QTabBar::tab {
                background: #444;
                border: 1px solid #555;
                padding: 5px 10px;
            }
            QTabBar::tab:selected {
                background: #666;
            }
            QLCDNumber {
                background-color: #333;
                color: #0f0;
                border: 1px solid #555;
            }
        """)
    
    def initUI(self):
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Create video display widget
        self.video_container = QWidget()
        video_layout = QVBoxLayout()
        self.video_widget = VideoWidget()
        self.video_widget.roi_selected.connect(self.update_roi_info)
        
        # Add info bar below video
        info_bar = QWidget()
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # FPS display
        fps_group = QWidget()
        fps_layout = QHBoxLayout()
        fps_layout.setContentsMargins(0, 0, 0, 0)
        fps_layout.addWidget(QLabel("FPS:"))
        self.fps_display = QLCDNumber()
        self.fps_display.setDigitCount(5)
        self.fps_display.setSegmentStyle(QLCDNumber.Flat)
        self.fps_display.setMinimumHeight(30)
        self.fps_display.setMaximumHeight(30)
        self.fps_display.setMaximumWidth(100)
        fps_layout.addWidget(self.fps_display)
        fps_group.setLayout(fps_layout)
        info_layout.addWidget(fps_group)
        
        # Recording time display
        rec_group = QWidget()
        rec_layout = QHBoxLayout()
        rec_layout.setContentsMargins(0, 0, 0, 0)
        self.rec_indicator = QLabel("● REC:")
        self.rec_indicator.setStyleSheet("color: red; font-weight: bold;")
        self.rec_indicator.setVisible(False)
        rec_layout.addWidget(self.rec_indicator)
        self.rec_time = QLCDNumber()
        self.rec_time.setDigitCount(5)
        self.rec_time.setSegmentStyle(QLCDNumber.Flat)
        self.rec_time.display("00:00")
        self.rec_time.setMinimumHeight(30)
        self.rec_time.setMaximumHeight(30)
        self.rec_time.setMaximumWidth(100)
        self.rec_time.setVisible(False)
        rec_layout.addWidget(self.rec_time)
        rec_group.setLayout(rec_layout)
        info_layout.addWidget(rec_group)
        
        # Resolution display
        res_label = QLabel("Resolution:")
        info_layout.addWidget(res_label)
        self.resolution_label = QLabel("---")
        info_layout.addWidget(self.resolution_label)
        
        info_layout.addStretch(1)
        
        # Camera selection
        info_layout.addWidget(QLabel("Camera:"))
        self.camera_selector = QComboBox()
        self.camera_selector.setMaximumWidth(100)
        self.detect_cameras()
        self.camera_selector.currentIndexChanged.connect(self.change_camera)
        info_layout.addWidget(self.camera_selector)
        
        info_bar.setLayout(info_layout)
        info_bar.setMaximumHeight(40)
        
        # Add video control buttons
        video_controls = QWidget()
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.pause_button.clicked.connect(self.toggle_pause)
        controls_layout.addWidget(self.pause_button)
        
        # Snapshot button
        snapshot_button = QPushButton("Snapshot")
        snapshot_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        snapshot_button.clicked.connect(self.take_snapshot)
        controls_layout.addWidget(snapshot_button)
        
        # Record button
        self.record_button = QPushButton("Start Recording")
        self.record_button.setIcon(QIcon())
        self.record_button.clicked.connect(self.toggle_recording)
        controls_layout.addWidget(self.record_button)
        
        video_controls.setLayout(controls_layout)
        video_controls.setMaximumHeight(40)
        
        # Add all components to video layout
        video_layout.addWidget(self.video_widget)
        video_layout.addWidget(info_bar)
        video_layout.addWidget(video_controls)
        
        self.video_container.setLayout(video_layout)
        
        # Create control panel with tabs
        self.control_panel = QTabWidget()
        self.control_panel.setMinimumWidth(300)
        self.control_panel.setMaximumWidth(400)
        
        # Create tabs
        self.create_filters_tab()
        self.create_roi_tab()
        self.create_detection_tab()
        self.create_settings_tab()
        
        # Add widgets to splitter
        splitter.addWidget(self.video_container)
        splitter.addWidget(self.control_panel)
        
        # Set splitter stretch factor
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Set main layout
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.statusBar.setStyleSheet("background-color: #444; color: white;")
        self.setStatusBar(self.statusBar)
        
        # Set window size
        self.resize(1200, 700)
    
    def create_filters_tab(self):
        """Create the filters tab in the control panel"""
        filters_tab = QWidget()
        filters_layout = QVBoxLayout()
        
        # Filter selection
        filter_group = QGroupBox("Image Filters")
        filter_layout = QVBoxLayout()
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "None", "Grayscale", "Sepia", "Blur", "Sharp", "Invert", 
            "Cartoon", "Sketch", "Emboss", "Binary"
        ])
        self.filter_combo.currentTextChanged.connect(self.change_filter)
        filter_layout.addWidget(QLabel("Select Filter:"))
        filter_layout.addWidget(self.filter_combo)
        
        # Canny Edge Detection
        canny_group = QGroupBox("Canny Edge Detection")
        canny_layout = QVBoxLayout()
        
        self.canny_checkbox = QCheckBox("Enable Canny Edge Detection")
        self.canny_checkbox.toggled.connect(self.toggle_canny)
        canny_layout.addWidget(self.canny_checkbox)
        
        # Add threshold sliders
        threshold_group = QGroupBox("Threshold Values")
        threshold_layout = QVBoxLayout()
        
        low_threshold_layout = QHBoxLayout()
        low_threshold_layout.addWidget(QLabel("Low Threshold:"))
        self.low_threshold_slider = QSlider(Qt.Horizontal)
        self.low_threshold_slider.setRange(0, 255)
        self.low_threshold_slider.setValue(50)
        self.low_threshold_slider.valueChanged.connect(self.update_low_threshold)
        self.low_threshold_label = QLabel("50")
        low_threshold_layout.addWidget(self.low_threshold_slider)
        low_threshold_layout.addWidget(self.low_threshold_label)
        threshold_layout.addLayout(low_threshold_layout)
        
        high_threshold_layout = QHBoxLayout()
        high_threshold_layout.addWidget(QLabel("High Threshold:"))
        self.high_threshold_slider = QSlider(Qt.Horizontal)
        self.high_threshold_slider.setRange(0, 255)
        self.high_threshold_slider.setValue(150)
        self.high_threshold_slider.valueChanged.connect(self.update_high_threshold)
        self.high_threshold_label = QLabel("150")
        high_threshold_layout.addWidget(self.high_threshold_slider)
        high_threshold_layout.addWidget(self.high_threshold_label)
        threshold_layout.addLayout(high_threshold_layout)
        
        # Add presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Presets:"))
        
        light_preset = QPushButton("Light Edges")
        light_preset.clicked.connect(lambda: self.apply_preset(20, 80))
        preset_layout.addWidget(light_preset)
        
        medium_preset = QPushButton("Medium")
        medium_preset.clicked.connect(lambda: self.apply_preset(50, 150))
        preset_layout.addWidget(medium_preset)
        
        strong_preset = QPushButton("Strong Edges")
        strong_preset.clicked.connect(lambda: self.apply_preset(80, 200))
        preset_layout.addWidget(strong_preset)
        
        threshold_layout.addLayout(preset_layout)
        threshold_group.setLayout(threshold_layout)
        canny_layout.addWidget(threshold_group)
        canny_group.setLayout(canny_layout)
        
        filter_layout.addWidget(canny_group)
        filter_group.setLayout(filter_layout)
        filters_layout.addWidget(filter_group)
        
        # Blur amount for certain filters
        blur_group = QGroupBox("Blur Amount")
        blur_layout = QHBoxLayout()
        
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setRange(1, 30)
        self.blur_slider.setSingleStep(2)
        self.blur_slider.setValue(5)
        blur_layout.addWidget(self.blur_slider)
        self.blur_label = QLabel("5")
        self.blur_slider.valueChanged.connect(lambda v: self.blur_label.setText(str(v)))
        blur_layout.addWidget(self.blur_label)
        
        blur_group.setLayout(blur_layout)
        filters_layout.addWidget(blur_group)
        
        filters_layout.addStretch(1)
        filters_tab.setLayout(filters_layout)
        
        self.control_panel.addTab(filters_tab, "Filters")
    
    def create_roi_tab(self):
        """Create the ROI tab in the control panel"""
        roi_tab = QWidget()
        roi_layout = QVBoxLayout()
        
        # ROI instructions
        instructions = QLabel("Click and drag on the video to select a region of interest. "
                             "Operations will only be applied to this area.")
        instructions.setWordWrap(True)
        roi_layout.addWidget(instructions)
        
        # Current ROI info
        roi_info_group = QGroupBox("Current ROI")
        roi_info_layout = QVBoxLayout()
        
        self.roi_info_label = QLabel("No ROI selected")
        roi_info_layout.addWidget(self.roi_info_label)
        
        roi_coords_layout = QHBoxLayout()
        roi_coords_layout.addWidget(QLabel("Size:"))
        self.roi_size_label = QLabel("0 x 0")
        roi_coords_layout.addWidget(self.roi_size_label)
        roi_coords_layout.addStretch(1)
        roi_info_layout.addLayout(roi_coords_layout)
        
        # ROI actions
        roi_actions_layout = QHBoxLayout()
        
        self.clear_roi_button = QPushButton("Clear ROI")
        self.clear_roi_button.clicked.connect(self.clear_roi)
        roi_actions_layout.addWidget(self.clear_roi_button)
        
        self.crop_to_roi_button = QPushButton("Crop To ROI")
        self.crop_to_roi_button.clicked.connect(self.crop_to_roi)
        self.crop_to_roi_button.setEnabled(False)
        roi_actions_layout.addWidget(self.crop_to_roi_button)
        
        roi_info_layout.addLayout(roi_actions_layout)
        roi_info_group.setLayout(roi_info_layout)
        roi_layout.addWidget(roi_info_group)
        
        roi_layout.addStretch(1)
        roi_tab.setLayout(roi_layout)
        
        self.control_panel.addTab(roi_tab, "ROI")
    
    def create_detection_tab(self):
        """Create the detection tab in the control panel"""
        detection_tab = QWidget()
        detection_layout = QVBoxLayout()
        
        # Face detection
        face_group = QGroupBox("Face Detection")
        face_layout = QVBoxLayout()
        
        self.face_checkbox = QCheckBox("Enable Face Detection")
        self.face_checkbox.toggled.connect(self.toggle_face_detection)
        face_layout.addWidget(self.face_checkbox)
        
        face_options_layout = QHBoxLayout()
        face_options_layout.addWidget(QLabel("Min Size:"))
        self.face_min_size = QSpinBox()
        self.face_min_size.setRange(10, 500)
        self.face_min_size.setValue(50)
        face_options_layout.addWidget(self.face_min_size)
        
        face_options_layout.addWidget(QLabel("Scale:"))
        self.face_scale = QSpinBox()
        self.face_scale.setRange(11, 20)
        self.face_scale.setValue(13)
        self.face_scale.setSingleStep(1)
        face_options_layout.addWidget(self.face_scale)
        face_layout.addLayout(face_options_layout)
        
        face_group.setLayout(face_layout)
        detection_layout.addWidget(face_group)
        
        # Motion detection settings could be added here in the future
        
        detection_layout.addStretch(1)
        detection_tab.setLayout(detection_layout)
        
        self.control_panel.addTab(detection_tab, "Detection")
    
    def create_settings_tab(self):
        """Create the settings tab in the control panel"""
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()
        
        # Camera settings
        camera_group = QGroupBox("Camera Settings")
        camera_layout = QVBoxLayout()
        
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("Resolution:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "Default", "640x480", "800x600", "1280x720", "1920x1080"
        ])
        self.resolution_combo.currentTextChanged.connect(self.change_resolution)
        resolution_layout.addWidget(self.resolution_combo)
        camera_layout.addLayout(resolution_layout)
        
        # FPS limit slider
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS Limit:"))
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setRange(1, 60)
        self.fps_slider.setValue(30)
        self.fps_slider.valueChanged.connect(self.change_fps_limit)
        fps_layout.addWidget(self.fps_slider)
        self.fps_value = QLabel("30")
        fps_layout.addWidget(self.fps_value)
        camera_layout.addLayout(fps_layout)
        
        camera_group.setLayout(camera_layout)
        settings_layout.addWidget(camera_group)
        
        # Output settings
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout()
        
        snapshot_path_layout = QHBoxLayout()
        snapshot_path_layout.addWidget(QLabel("Snapshot Path:"))
        self.snapshot_path = QLabel("./snapshots")
        snapshot_path_layout.addWidget(self.snapshot_path)
        browse_button = QPushButton("...")
        browse_button.setMaximumWidth(40)
        browse_button.clicked.connect(self.browse_snapshot_dir)
        snapshot_path_layout.addWidget(browse_button)
        output_layout.addLayout(snapshot_path_layout)
        
        # Video format selector
        video_format_layout = QHBoxLayout()
        video_format_layout.addWidget(QLabel("Video Format:"))
        self.video_format = QComboBox()
        self.video_format.addItems(["AVI (XVID)", "MP4 (H.264)", "MKV (XVID)"])
        video_format_layout.addWidget(self.video_format)
        output_layout.addLayout(video_format_layout)
        
        output_group.setLayout(output_layout)
        settings_layout.addWidget(output_group)
        
        # About section
        about_group = QGroupBox("About VisionDesk")
        about_layout = QVBoxLayout()
        
        version_label = QLabel("Version: 1.0.0")
        version_label.setStyleSheet("font-weight: bold;")
        about_layout.addWidget(version_label)
        
        about_text = QLabel("VisionDesk is an advanced computer vision application "
                           "that allows real-time image processing and analysis.")
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)
        
        credits_label = QLabel("Created for Python Computer Vision Course")
        credits_label.setStyleSheet("font-style: italic;")
        about_layout.addWidget(credits_label)
        
        about_group.setLayout(about_layout)
        settings_layout.addWidget(about_group)
        
        settings_layout.addStretch(1)
        settings_tab.setLayout(settings_layout)
        
        self.control_panel.addTab(settings_tab, "Settings")
    
    def detect_cameras(self):
        """Detect available cameras"""
        self.camera_selector.clear()
        
        # Check for available cameras (usually 0-9 are enough for most systems)
        available_cameras = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
        
        if available_cameras:
            for camera_idx in available_cameras:
                self.camera_selector.addItem(f"Camera {camera_idx}")
        else:
            self.camera_selector.addItem("No cameras found")
    
    def open_camera(self):
        """Open the selected camera"""
        if self.camera is not None:
            self.camera.release()
        
        self.camera = cv2.VideoCapture(self.camera_index)
        if not self.camera.isOpened():
            self.show_status("Error: Could not open camera.")
            return False
        
        # Try to set resolution if not default
        current_res = self.resolution_combo.currentText()
        if current_res != "Default":
            try:
                width, height = map(int, current_res.split('x'))
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            except ValueError:
                pass
        
        return True
    
    def change_camera(self, index):
        """Change the active camera"""
        camera_text = self.camera_selector.currentText()
        if "Camera" in camera_text:
            try:
                self.camera_index = int(camera_text.split(" ")[1])
                self.open_camera()
                self.show_status(f"Switched to Camera {self.camera_index}")
            except (ValueError, IndexError):
                self.show_status("Invalid camera selection")
    
    def change_resolution(self, resolution):
        """Change camera resolution"""
        if resolution == "Default" or self.camera is None:
            return
        
        try:
            width, height = map(int, resolution.split('x'))
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.show_status(f"Resolution set to {resolution}")
        except ValueError:
            self.show_status("Invalid resolution format")
    
    def change_fps_limit(self, value):
        """Change the FPS limit for the camera feed"""
        self.fps_value.setText(str(value))
        
        # Update timer interval
        if value > 0:
            interval = int(1000 / value)
            self.timer.setInterval(interval)
            self.show_status(f"FPS limit set to {value}")
    
    def toggle_pause(self):
        """Toggle pause/resume of the video feed"""
        self.pause_video = not self.pause_video
        
        if self.pause_video:
            self.pause_button.setText("Resume")
            self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.show_status("Video paused")
        else:
            self.pause_button.setText("Pause")
            self.pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.show_status("Video resumed")
    
    def toggle_canny(self, checked):
        """Toggle Canny edge detection"""
        self.use_canny = checked
        if checked:
            self.show_status("Canny edge detection enabled")
        else:
            self.show_status("Canny edge detection disabled")
    
    def toggle_face_detection(self, checked):
        """Toggle face detection"""
        self.detect_faces = checked
        if checked:
            self.show_status("Face detection enabled")
        else:
            self.show_status("Face detection disabled")
    
    def update_low_threshold(self, value):
        """Update low threshold for Canny edge detection"""
        self.low_threshold = value
        self.low_threshold_label.setText(str(value))
    
    def update_high_threshold(self, value):
        """Update high threshold for Canny edge detection"""
        self.high_threshold = value
        self.high_threshold_label.setText(str(value))
    
    def apply_preset(self, low, high):
        """Apply preset values for Canny thresholds"""
        self.low_threshold_slider.setValue(low)
        self.high_threshold_slider.setValue(high)
        self.show_status(f"Applied preset: {low}/{high}")
    
    def clear_roi(self):
        """Clear the current ROI selection"""
        self.video_widget.roi_selector.clear_selection()
        self.roi_info_label.setText("No ROI selected")
        self.roi_size_label.setText("0 x 0")
        self.crop_to_roi_button.setEnabled(False)
        self.show_status("ROI cleared")
    
    def update_roi_info(self):
        """Update ROI information display"""
        roi = self.video_widget.roi_selector.get_roi()
        if roi:
            x1, y1, x2, y2 = roi
            width = x2 - x1
            height = y2 - y1
            self.roi_info_label.setText(f"ROI: ({x1}, {y1}) to ({x2}, {y2})")
            self.roi_size_label.setText(f"{width} x {height}")
            self.crop_to_roi_button.setEnabled(True)
            self.show_status(f"ROI selected: {width}x{height}")
    
    def crop_to_roi(self):
        """Crop the view to the selected ROI"""
        if self.current_frame is None:
            return
            
        roi = self.video_widget.roi_selector.get_roi()
        if roi:
            x1, y1, x2, y2 = roi
            # Store the cropped dimensions
            self.cropped_frame = True
            self.show_status("Cropped to ROI")
    
    def change_filter(self, filter_name):
        """Change the current image filter"""
        self.current_filter = filter_name
        self.show_status(f"Filter changed to {filter_name}")
    
    def take_snapshot(self):
        """Take a snapshot of the current frame"""
        if self.current_frame is None:
            self.show_status("No frame available for snapshot")
            return
        
        # Create directory if it doesn't exist
        os.makedirs('snapshots', exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshots/visiondesk_snap_{timestamp}.jpg"
        
        # Save the snapshot
        cv2.imwrite(filename, self.current_frame)
        self.snapshot_counter += 1
        
        self.show_status(f"Snapshot saved: {filename}")
    
    def toggle_recording(self):
        """Toggle video recording on/off"""
        if self.recorder.is_recording:
            # Stop recording
            filename = self.recorder.stop_recording()
            self.record_button.setText("Start Recording")
            self.record_button.setIcon(QIcon())  # Empty icon or a standard one like SP_DialogSaveButton
            self.rec_indicator.setVisible(False)
            self.rec_time.setVisible(False)
            self.show_status(f"Recording saved: {filename}")
        else:
            # Start recording
            if self.current_frame is None:
                self.show_status("No frame available for recording")
                return
                
            h, w = self.current_frame.shape[:2]
            filename = self.recorder.start_recording((w, h))
            if filename:
                self.record_button.setText("Stop Recording")
                self.record_button.setIcon(QIcon())
                self.rec_indicator.setVisible(True)
                self.rec_time.setVisible(True)
                self.show_status(f"Recording started: {filename}")
    
    def update_recording_time(self):
        """Update the recording time display"""
        if self.recorder.is_recording:
            seconds = self.recorder.get_recording_time()
            minutes = seconds // 60
            seconds = seconds % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            self.rec_time.display(time_str)
    
    def browse_snapshot_dir(self):
        """Browse for snapshot directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Snapshot Directory", ".",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if directory:
            self.snapshot_path.setText(directory)
            self.show_status(f"Snapshot directory changed to: {directory}")
    
    def show_status(self, message, timeout=3000):
        """Show a message in the status bar"""
        self.statusBar.showMessage(message)
        self.status_timer.start(timeout)
    
    def clear_status(self):
        """Clear the status bar message"""
        self.statusBar.clearMessage()
        self.status_timer.stop()
    
    def center_window(self):
        """Center the window on the screen"""
        frame_geometry = self.frameGeometry()
        screen_center = self.screen().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())
    
    def update_frame(self):
        """Update the video frame"""
        if self.camera is None or not self.camera.isOpened():
            return
        
        # Skip frame update if paused
        if self.pause_video:
            if self.current_frame is not None:
                # Just redraw the current frame with any UI changes
                processed_frame = self.process_frame(self.current_frame.copy())
                self.display_frame(processed_frame)
            return
        
        # Capture new frame
        ret, frame = self.camera.read()
        if not ret:
            self.show_status("Error: Failed to capture image")
            return
        
        # Update FPS counter
        fps = self.fps_counter.update()
        self.fps_display.display(f"{fps:.1f}")
        
        # Update recording time if recording
        self.update_recording_time()
        
        # Write frame to video if recording
        if self.recorder.is_recording:
            self.recorder.write_frame(frame)
        
        # Update resolution label
        h, w = frame.shape[:2]
        self.resolution_label.setText(f"{w}x{h}")
        
        # Flip the frame horizontally for a more natural view
        frame = cv2.flip(frame, 1)
        
        # Store the original frame
        self.current_frame = frame.copy()
        
        # Process frame based on current settings
        processed_frame = self.process_frame(frame)
        
        # Draw ROI if it exists
        processed_frame = self.video_widget.roi_selector.draw_roi(processed_frame)
        
        # Convert the frame to Qt format and display it
        self.display_frame(processed_frame)
    
    def process_frame(self, frame):
        """Process the frame based on current settings"""
        if frame is None:
            return None
            
        # Get ROI if available
        roi = self.video_widget.roi_selector.get_roi()
        processed = frame.copy()
        
        # Apply filters
        if roi:
            # Extract ROI
            x1, y1, x2, y2 = roi
            roi_frame = frame[y1:y2, x1:x2].copy()
            
            # Apply processing to ROI
            processed_roi = self.apply_processing(roi_frame)
            
            # Replace the ROI area in the original frame
            processed[y1:y2, x1:x2] = processed_roi
        else:
            # Apply processing to the entire frame
            processed = self.apply_processing(frame)
        
        return processed
    
    def apply_processing(self, frame):
        """Apply various processing options to the frame"""
        # Apply selected filter
        if self.current_filter != "None":
            frame = self.apply_filter(frame, self.current_filter)
        
        # Apply Canny edge detection if enabled
        if self.use_canny:
            # Convert frame to grayscale for Canny edge detection
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
                
            edges = cv2.Canny(gray, self.low_threshold, self.high_threshold)
            
            # Convert edges back to BGR for display
            frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # Apply face detection if enabled
        if self.detect_faces:
            frame = self.detect_faces_in_frame(frame)
        
        return frame
    
    def apply_filter(self, frame, filter_name):
        """Apply the selected filter to the frame"""
        if filter_name == "Grayscale":
            return cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        
        elif filter_name == "Sepia":
            # Sepia filter matrix
            sepia_kernel = np.array([
                [0.272, 0.534, 0.131],
                [0.349, 0.686, 0.168],
                [0.393, 0.769, 0.189]
            ])
            sepia_img = cv2.transform(frame, sepia_kernel)
            return np.clip(sepia_img, 0, 255).astype(np.uint8)
        
        elif filter_name == "Blur":
            blur_amount = self.blur_slider.value()
            if blur_amount % 2 == 0:  # Ensure odd number for Gaussian blur
                blur_amount += 1
            return cv2.GaussianBlur(frame, (blur_amount, blur_amount), 0)
        
        elif filter_name == "Sharp":
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            return cv2.filter2D(frame, -1, kernel)
        
        elif filter_name == "Invert":
            return cv2.bitwise_not(frame)
        
        elif filter_name == "Cartoon":
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply median blur
            gray = cv2.medianBlur(gray, 5)
            
            # Detect edges
            edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                         cv2.THRESH_BINARY, 9, 9)
            
            # Apply bilateral filter for cartoon effect
            color = cv2.bilateralFilter(frame, 9, 300, 300)
            
            # Combine edges with color image
            cartoon = cv2.bitwise_and(color, color, mask=edges)
            return cartoon
        
        elif filter_name == "Sketch":
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Invert grayscale image
            inv_gray = 255 - gray
            
            # Apply Gaussian blur
            blur_amount = self.blur_slider.value()
            if blur_amount % 2 == 0:
                blur_amount += 1
            blurred = cv2.GaussianBlur(inv_gray, (blur_amount, blur_amount), 0)
            
            # Invert blurred image
            inv_blurred = 255 - blurred
            
            # Create pencil sketch
            sketch = cv2.divide(gray, inv_blurred, scale=256.0)
            
            # Convert back to BGR
            return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
        
        elif filter_name == "Emboss":
            kernel = np.array([[-2,-1,0], [-1,1,1], [0,1,2]])
            emboss = cv2.filter2D(frame, -1, kernel)
            return emboss
        
        elif filter_name == "Binary":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        
        return frame
    
    def detect_faces_in_frame(self, frame):
        """Detect faces in the frame"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        min_size = self.face_min_size.value()
        scale_factor = self.face_scale.value() / 10.0  # Convert 11-20 to 1.1-2.0
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=scale_factor,
            minNeighbors=5,
            minSize=(min_size, min_size)
        )
        
        # Draw rectangles around detected faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Draw label
            cv2.putText(frame, "Face", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 255, 0), 2)
        
        return frame
    
    def display_frame(self, frame):
        """Convert and display frame in the GUI"""
        if frame is None:
            return
            
        # Convert from BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to QImage
        h, w, ch = rgb_frame.shape
        bytesPerLine = ch * w
        qImg = QImage(rgb_frame.data, w, h, bytesPerLine, QImage.Format_RGB888)
        
        # Scale the QImage to fit the video widget
        scaled_pixmap = QPixmap.fromImage(qImg).scaled(
            self.video_widget.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        # Display the image
        self.video_widget.setPixmap(scaled_pixmap)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Release the camera and other resources when closing the application
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        
        if hasattr(self, 'camera') and self.camera is not None:
            self.camera.release()
            
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = VisionDesk()
    window.show()
    sys.exit(app.exec_())