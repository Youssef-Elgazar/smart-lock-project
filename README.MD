# Smart Lock System

A facial recognition-based smart lock system with admin controls and logging.

## Overview

This implementation shares a single camera stream between two applications:
1. `face_recognition_app.py` - The Streamlit web interface that captures and processes camera frames
2. `admin_control.py` - The admin control panel that displays the same camera feed

## How It Works

The system uses MQTT to share the camera stream:

1. `face_recognition_app.py` captures frames from the camera
2. It processes these frames for face recognition
3. It also compresses and publishes each frame to the MQTT topic `smartlock/camera`
4. `admin_control.py` subscribes to this topic and displays the frames

## Environment Setup

Inside the project folder, run the following commands:

```powershell
# Create virtual environment with system packages
python -m venv --system-site-packages iot

# Activate virtual environment
iot\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt --only-binary=:all:
pip install paho-mqtt==1.5.1
```

## Requirements

- MQTT Broker (Mosquitto) running on your machine
- All Python dependencies as listed in your requirements.txt

## Setup Instructions

### 1. Install & Start Mosquitto MQTT Broker

#### On Windows:
1. Download Mosquitto from: https://mosquitto.org/download/
2. Install it following the installer's instructions
3. Start the service:
   ```
   net start mosquitto
   ```

#### On Raspberry Pi:
```bash
sudo apt-get install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

### 2. Verify Mosquitto is Running

#### On Windows:
```
netstat -an | findstr 1883
```

#### On Raspberry Pi:
```bash
sudo systemctl status mosquitto
```

## Running the System

Open 4 separate terminal windows in the project folder and run each component:

1. Start the logging system:
```powershell
python system_logs.py
```

2. Start the face registration tool:
```powershell
python register_faces.py
```

3. Launch the admin control panel:
```powershell
python admin_control.py
```

4. Start the main face recognition app:
```powershell
streamlit run face_recognition_app.py
```

Each component must be running for the system to work properly. The system uses MQTT for communication between components, so make sure you have a MQTT broker (like Mosquitto) running locally.

## Troubleshooting

### No Camera Feed in Admin Panel
- Make sure `face_recognition_app.py` is running first
- Verify Mosquitto is running
- Check for error messages in both console windows

### Connection Errors
- Ensure Mosquitto is running on port 1883
- Check firewall settings if applications are on different machines

### Performance Issues
- Frame quality is reduced to 50% JPEG quality to improve performance
- If needed, you can further reduce the frame rate or resolution in the code