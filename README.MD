# README: Shared Camera System Setup

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

### 3. Starting the Applications

1. First, start the face recognition app:
   ```
   python face_recognition_app.py
   ```

2. Then, in a separate terminal, start the admin control panel:
   ```
   python admin_control.py
   ```

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