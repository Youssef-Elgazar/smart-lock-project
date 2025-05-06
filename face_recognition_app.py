# face_recognition_app.py
import streamlit as st
import cv2
import numpy as np
import os
import sqlite3
import datetime
from PIL import Image
import time

st.set_page_config(layout="wide")  # Moved to top

# Initialize session state
if 'marked_students' not in st.session_state:
    st.session_state.marked_students = set()
if 'recently_marked' not in st.session_state:
    st.session_state.recently_marked = {}
if 'camera_running' not in st.session_state:
    st.session_state.camera_running = False

# Load recognizer and label map
@st.cache_resource
def load_recognizer():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    label_map = {}

    if os.path.exists("data/trained_model.yml"):
        recognizer.read("data/trained_model.yml")

    if os.path.exists("data/label_mapping.txt"):
        with open("data/label_mapping.txt", "r") as f:
            for line in f:
                name, id = line.strip().split(',')
                label_map[int(id)] = name

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    return recognizer, label_map, face_cascade

recognizer, label_map, face_cascade = load_recognizer()

# Function to mark attendance
def mark_attendance(name):
    if name == "Unknown":
        return False

    now = datetime.datetime.now()

    if name in st.session_state.recently_marked:
        elapsed = (now - st.session_state.recently_marked[name]).total_seconds()
        if elapsed < 60:  # 1 minute cooldown
            return True

    st.session_state.recently_marked[name] = now
    current_date = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M:%S')

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM attendance WHERE name = ? AND date = ?", (name, current_date))
    already_marked = cursor.fetchone()

    if not already_marked:
        cursor.execute("INSERT INTO attendance (name, time, date) VALUES (?, ?, ?)", (name, current_time, current_date))
        conn.commit()
        st.session_state.marked_students.add(name)
    conn.close()
    return True

# Main app
def main():
    st.title("Face Recognition Attendance System")

    col1, col2 = st.columns([2, 1])

    camera_placeholder = col1.empty()
    feedback_placeholder = col2.empty()
    marked_list_placeholder = col2.empty()

    start_button = col2.button("Start Camera")
    stop_button = col2.button("Stop Camera")

    if start_button:
        st.session_state.camera_running = True
    if stop_button:
        st.session_state.camera_running = False

    if st.session_state.camera_running:
        cap = cv2.VideoCapture(0)

        while st.session_state.camera_running:
            ret, frame = cap.read()
            if not ret:
                st.warning("Unable to access webcam.")
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            recognized_name = None
            for (x, y, w, h) in faces:
                size = max(w, h)
                center_x, center_y = x + w // 2, y + h // 2
                x_new = max(center_x - size // 2, 0)
                y_new = max(center_y - size // 2, 0)
                x_new = min(x_new, gray.shape[1] - size)
                y_new = min(y_new, gray.shape[0] - size)

                face_roi = gray[y_new:y_new + size, x_new:x_new + size]

                try:
                    label, confidence = recognizer.predict(face_roi)
                    if confidence < 70 and label in label_map:
                        recognized_name = label_map[label]
                        mark_attendance(recognized_name)
                    else:
                        recognized_name = "Unknown"
                except:
                    recognized_name = "Unknown"

                cv2.rectangle(rgb_frame, (x_new, y_new), (x_new + size, y_new + size), (0, 255, 0), 2)
                cv2.putText(rgb_frame, recognized_name, (x_new, y_new - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # Display frame
            camera_placeholder.image(rgb_frame, channels="RGB", use_column_width=True, caption="Live Camera Feed")

            # Feedback
            if recognized_name and recognized_name != "Unknown":
                feedback_placeholder.success(f"✅ Welcome, {recognized_name}!")
            elif recognized_name == "Unknown":
                feedback_placeholder.error("❌ Face not recognized")
            else:
                feedback_placeholder.info("👋 Looking for faces...")

            if st.session_state.marked_students:
                marked_list_placeholder.markdown("### Marked Present Today:")
                for i, name in enumerate(sorted(st.session_state.marked_students), 1):
                    marked_list_placeholder.markdown(f"{i}. {name}")

            # Small delay to avoid overloading CPU
            time.sleep(0.03)

        cap.release()
        st.success("Camera stopped")

if __name__ == "__main__":
    main()
