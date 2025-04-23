Project Setup Instructions

**General Requirements (Both Platforms):**

- Python 3.10 or later
- pip (Python package installer)

**I. Windows Setup**

1.  **Install Dependencies:**

    - **Virtual Environment (Recommended):**
      - Install `virtualenv` (if needed):
        ```powershell
        pip install virtualenv
        ```
      - Create:
        ```powershell
        python -m venv venv
        ```
      - Activate:
        ```powershell
        .\venv\Scripts\activate
        ```
    - Install packages using `requirements.txt`:
      ```powershell
      pip install -r requirements.txt
      ```

2.  **Running the Code:**

    - Register faces:
      ```powershell
      python Register_faces.py
      ```
    - Run attendance:
      ```powershell
      python attendance_taker.py
      ```

**II. Raspberry Pi Setup**

1.  **Install Dependencies:**

    - Update system:
      ```bash
      sudo apt-get update
      sudo apt-get upgrade
      ```
    - Install Python 3 and pip:
      ```bash
      sudo apt-get install python3 python3-pip
      ```
    - Install `virtualenv` (recommended):
      ```bash
      sudo apt-get install python3-venv
      ```
    - Create and activate virtual environment:
      ```bash
      python3 -m venv venv
      source venv/bin/activate
      ```
    - Install packages using `requirements.txt`:
      ```bash
      pip3 install -r requirements.txt
      ```
    - Install OpenCV dependencies:
      ```bash
      sudo apt-get install libatlas-base-dev libjasper-dev libqtgui4 libqt4-test
      ```

2.  **Running the Code:**

    - Register faces:
      ```bash
      python3 Register_faces.py
      ```
    - Run attendance:
      ```bash
      python3 attendance_taker.py
      ```

**III. `requirements.txt`:**

```text
opencv-python
numpy
Pillow
tkinter
```
