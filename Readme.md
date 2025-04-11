# VisionDesk

A Python GUI-based vision application that demonstrates real-time computer vision capabilities using OpenCV and PyQt5.

## Features

- Real-time webcam feed display
- Toggle between Original Camera Feed and Canny Edge Detection
- Region of Interest (ROI) selection for targeted processing
- Real-time adjustment of Canny Edge Detection threshold values
- Intuitive user interface

## Prerequisites

- Python 3.6 or higher
- Webcam or camera connected to your computer

## Installation

### Using requirements.txt (Recommended)

The project includes a `requirements.txt` file that lists all necessary dependencies. This is the easiest way to set up the environment:

#### On Windows:

```bash

# Create virtual environment
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\activate

# Install dependencies from requirements.txt
pip install -r requirements.txt
```

#### On macOS/Linux:

```bash

# Create virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies from requirements.txt
pip install -r requirements.txt
```

### Manual Installation (Alternative)

If you prefer to install the dependencies manually:

```bash
# Activate your virtual environment first, then:
pip install opencv-python pyqt5
```

### Direct Installation (Not Recommended)

If you prefer not to use a virtual environment, you can install the dependencies directly:

```bash
pip install -r requirements.txt
```

## Running the Application

1. Save the provided Python code to a file named `vision_desk.py`
2. Ensure your virtual environment is activated (if using one)
3. Run the application:

```bash
python vision_desk.py
```

## Usage Instructions

1. The application will start and display your webcam feed.
2. Control Panel (right side):
   - **Canny Edge Detection**: Toggle to enable/disable edge detection
   - **Threshold Values**: Adjust low and high thresholds for the Canny algorithm
   - **Region of Interest (ROI)**: Shows coordinates of selected region
   
3. To select a Region of Interest:
   - Click and drag on the video feed
   - The selected area will be highlighted with a green rectangle
   - When Canny Edge Detection is enabled, it will be applied only to the selected region
   
4. To clear the ROI selection, click the "Clear ROI" button.

## Project Structure

```
visiondesk/
├── venv/                   # Virtual environment (after creation)
├── .gitignore              # Git ignore file
├── requirements.txt        # Project dependencies
├── vision_desk.py          # Main application code
└── README.md               # This file
```

## Troubleshooting

- **Camera Access Error**: If the application shows "Error: Could not open camera", ensure your webcam is properly connected and not being used by another application.
- **Performance Issues**: If the application runs slowly, try reducing the resolution in the code or ensure your computer meets the minimum requirements.
- **Missing Dependencies**: If you get import errors, verify that all required packages are installed by running `pip list` and checking for opencv-python and pyqt5.

## License

This project is open source and available for educational and personal use.

## Acknowledgments

- OpenCV for computer vision capabilities
- PyQt5 for the GUI framework