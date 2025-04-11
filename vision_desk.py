import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QSlider, 
                             QCheckBox, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap


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
        return frame


class VideoWidget(QLabel):
    """Custom widget to display and interact with camera feed"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.roi_selector = ROISelector()
        self.setMouseTracking(True)
        self.setStyleSheet("border: 1px solid gray")
        self.setMinimumSize(640, 480)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            # Convert position from Qt coordinates to image coordinates
            img_size = self.pixmap().size() if self.pixmap() else None
            if img_size:
                # Scale factor between widget size and pixmap size
                scale_x = self.width() / img_size.width()
                scale_y = self.height() / img_size.height()
                
                # Widget coordinates
                pos_x, pos_y = pos.x(), pos.y()
                
                # Convert to image coordinates
                img_x = int(pos_x / scale_x)
                img_y = int(pos_y / scale_y)
                
                self.roi_selector.start_selection(img_x, img_y)
    
    def mouseMoveEvent(self, event):
        if self.roi_selector.selecting:
            pos = event.pos()
            # Convert position from Qt coordinates to image coordinates
            img_size = self.pixmap().size() if self.pixmap() else None
            if img_size:
                # Scale factor between widget size and pixmap size
                scale_x = self.width() / img_size.width()
                scale_y = self.height() / img_size.height()
                
                # Widget coordinates
                pos_x, pos_y = pos.x(), pos.y()
                
                # Convert to image coordinates
                img_x = int(pos_x / scale_x)
                img_y = int(pos_y / scale_y)
                
                self.roi_selector.update_selection(img_x, img_y)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.roi_selector.finish_selection()


class VisionDesk(QMainWindow):
    """Main application window for VisionDesk"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
        # Initialize camera
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            print("Error: Could not open camera.")
            sys.exit(1)
        
        # Set up timer for updating the camera feed
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update every 30ms (~33 fps)
        
        # Initialize variables
        self.use_canny = False
        self.low_threshold = 50
        self.high_threshold = 150
    
    def initUI(self):
        # Set up the main window
        self.setWindowTitle('VisionDesk')
        self.setGeometry(100, 100, 1000, 600)
        
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Create video display widget
        self.video_widget = VideoWidget()
        
        # Create control panel
        control_panel = QWidget()
        control_panel_layout = QVBoxLayout()
        
        # Add Canny Edge toggle
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
        
        threshold_group.setLayout(threshold_layout)
        canny_layout.addWidget(threshold_group)
        canny_group.setLayout(canny_layout)
        control_panel_layout.addWidget(canny_group)
        
        # Add ROI controls
        roi_group = QGroupBox("Region of Interest (ROI)")
        roi_layout = QVBoxLayout()
        
        self.roi_info_label = QLabel("No ROI selected")
        roi_layout.addWidget(self.roi_info_label)
        
        roi_button_layout = QHBoxLayout()
        self.clear_roi_button = QPushButton("Clear ROI")
        self.clear_roi_button.clicked.connect(self.clear_roi)
        roi_button_layout.addWidget(self.clear_roi_button)
        roi_layout.addLayout(roi_button_layout)
        
        roi_group.setLayout(roi_layout)
        control_panel_layout.addWidget(roi_group)
        
        # Add a spacer to push controls to the top
        control_panel_layout.addStretch(1)
        
        # Set layouts
        control_panel.setLayout(control_panel_layout)
        control_panel.setFixedWidth(300)
        
        main_layout.addWidget(self.video_widget)
        main_layout.addWidget(control_panel)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def toggle_canny(self, checked):
        self.use_canny = checked
    
    def update_low_threshold(self, value):
        self.low_threshold = value
        self.low_threshold_label.setText(str(value))
    
    def update_high_threshold(self, value):
        self.high_threshold = value
        self.high_threshold_label.setText(str(value))
    
    def clear_roi(self):
        self.video_widget.roi_selector.clear_selection()
        self.roi_info_label.setText("No ROI selected")
    
    def update_frame(self):
        ret, frame = self.camera.read()
        if not ret:
            print("Error: Failed to capture image")
            return
        
        # Flip the frame horizontally for a more natural view
        frame = cv2.flip(frame, 1)
        
        # Process frame based on current settings
        processed_frame = self.process_frame(frame.copy())
        
        # Draw ROI if it exists
        processed_frame = self.video_widget.roi_selector.draw_roi(processed_frame)
        
        # Update ROI info label
        roi = self.video_widget.roi_selector.get_roi()
        if roi:
            x1, y1, x2, y2 = roi
            self.roi_info_label.setText(f"ROI: ({x1}, {y1}) to ({x2}, {y2})")
        
        # Convert the frame to Qt format and display it
        self.display_frame(processed_frame)
    
    def process_frame(self, frame):
        # Get ROI if available
        roi = self.video_widget.roi_selector.get_roi()
        
        if self.use_canny:
            # Convert frame to grayscale for Canny edge detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if roi:
                # Extract ROI
                x1, y1, x2, y2 = roi
                roi_gray = gray[y1:y2, x1:x2]
                
                # Apply Canny edge detection to ROI
                edges_roi = cv2.Canny(roi_gray, self.low_threshold, self.high_threshold)
                
                # Convert edges back to BGR for display
                edges_roi_bgr = cv2.cvtColor(edges_roi, cv2.COLOR_GRAY2BGR)
                
                # Replace the ROI area in the original frame
                frame[y1:y2, x1:x2] = edges_roi_bgr
            else:
                # Apply Canny edge detection to the entire frame
                edges = cv2.Canny(gray, self.low_threshold, self.high_threshold)
                frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        return frame
    
    def display_frame(self, frame):
        # Convert frame from BGR to RGB
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
        # Release the camera when closing the application
        if hasattr(self, 'camera'):
            self.camera.release()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VisionDesk()
    window.show()
    sys.exit(app.exec_())