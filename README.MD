# Smart Lock Project - Setup Instructions

## General Requirements
- Python 3.10 or later
- pip (Python package installer)

## I. Windows Setup

### 1. Set Up Virtual Environment

Create a virtual environment with system site-packages:
```powershell
python -m venv --system-site-packages iot
```

Activate the virtual environment:
```powershell
.\iot\Scripts\Activate.ps1
```

> **Note:** If you encounter execution policy errors, you may need to run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
> ```

### 2. Install Dependencies

Install required packages:
```powershell
pip install --only-binary=:all: opencv-python==4.7.0.72 opencv-contrib-python==4.7.0.72 numpy Pillow==9.5.0 paho-mqtt==1.6.1 sqlalchemy==2.0.15 streamlit==1.22.0 pyserial==3.5
pip install tk-tools==0.21.0
```

Alternatively, if you have a requirements.txt file:
```powershell
pip install -r requirements.txt --only-binary=:all:
```

### 3. Running the Application

Register faces:
```powershell
python Register_faces.py
```

Run the attendance system:
```powershell
python attendance_taker.py
```

## II. Raspberry Pi Setup

### 1. Set Up System

Update your system:
```bash
sudo apt-get update
sudo apt-get upgrade
```

Install Python and dependencies:
```bash
sudo apt-get install python3 python3-pip
sudo apt-get install libatlas-base-dev libjasper-dev libqtgui4 libqt4-test
```

### 2. Set Up Virtual Environment

Install virtualenv:
```bash
sudo apt-get install python3-venv
```

Create a virtual environment with system site-packages:
```bash
python3 -m venv --system-site-packages iot
```

Activate the virtual environment:
```bash
source iot/bin/activate
```

### 3. Install Dependencies

Install required packages from requirements.txt:
```bash
pip3 install -r requirements.txt
```

### 4. Running the Application

Register faces:
```bash
python3 Register_faces.py
```

Run the attendance system:
```bash
python3 attendance_taker.py
```

## Troubleshooting

If you encounter build errors when installing packages on Windows:
1. Install Microsoft C++ Build Tools from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. During installation, select "C++ build tools" under Workloads
3. Restart your terminal and try installing the requirements again

## Project Components

- **OpenCV**: Computer vision for facial recognition
- **Pillow**: Image processing
- **MQTT**: IoT communication protocol
- **SQLAlchemy**: Database operations
- **Streamlit**: Web interface
- **PySerial**: Hardware communication