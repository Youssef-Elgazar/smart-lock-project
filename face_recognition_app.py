# face_recognition_app.py
import streamlit as st
import cv2
import numpy as np
import os
import sqlite3
import datetime
from PIL import Image
import time
import paho.mqtt.client as mqtt
import json
import base64
import threading
# For PC buzzer sound simulation
import winsound

st.set_page_config(layout="wide")

if 'marked_students' not in st.session_state:
    st.session_state.marked_students = set()
if 'recently_marked' not in st.session_state:
    st.session_state.recently_marked = {}
if 'camera_running' not in st.session_state:
    st.session_state.camera_running = False
if 'last_access' not in st.session_state:
    st.session_state.last_access = None
if 'admin_message' not in st.session_state:
    st.session_state.admin_message = None
if 'unknown_timeout' not in st.session_state:
    st.session_state.unknown_timeout = None
if 'unknown_timeout_until' not in st.session_state:
    st.session_state.unknown_timeout_until = None
if 'admin_action' not in st.session_state:
    st.session_state.admin_action = None
if 'is_locked' not in st.session_state:
    st.session_state.is_locked = True
if 'emergency_mode' not in st.session_state:
    st.session_state.emergency_mode = False

# Function to simulate buzzer on PC
def sound_alarm(duration=1000, frequency=800):
    """Simulate alarm sound on PC"""
    try:
        # Windows-specific sound (duration in ms, freq in Hz)
        winsound.Beep(frequency, duration)
    except:
        # Fallback for non-Windows systems
        print("ALARM SOUND: Cannot play on this system")

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client(client_id="WebApp")
        
        try:
            self.client.connect("localhost", 1883)
            self.client.subscribe([
                ("smartlock/events", 0), 
                ("smartlock/control", 0),
                ("smartlock/admin_action", 0)  # New subscription for admin actions
            ])
            self.client.on_message = self.on_message
            print("Connected to MQTT broker")
        except ConnectionRefusedError:
            st.error("Failed to connect to MQTT broker. Is the broker running?")
            print("Failed to connect to MQTT broker. Is Mosquitto running?")
        
    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            if msg.topic == "smartlock/events":
                st.session_state.last_access = data
            elif msg.topic == "smartlock/control":
                if data["source"] == "admin":
                    if data["command"] == "unlock":
                        st.session_state.admin_message = "✅ Access Allowed by Admin"
                        st.session_state.is_locked = False
                        # Reset emergency mode if it was active
                        st.session_state.emergency_mode = False
                    elif data["command"] == "lockdown":
                        st.session_state.admin_message = "❌ Access Denied by Admin. Contacting emergency services."
                        st.session_state.is_locked = True
                        st.session_state.emergency_mode = True
                        # Sound the alarm
                        threading.Thread(target=sound_alarm, args=(2000, 1000)).start()
            elif msg.topic == "smartlock/admin_action":
                # Handle admin actions from system_logs
                if data["action"] == "allowed":
                    st.session_state.admin_action = {
                        "message": data["message"] if "message" in data else "✅ Access Allowed by Admin",
                        "timestamp": data["timestamp"]
                    }
                    st.session_state.is_locked = False
                    # Reset emergency mode if it was active
                    st.session_state.emergency_mode = False
                elif data["action"] == "denied":
                    st.session_state.admin_action = {
                        "message": data["message"] if "message" in data else "❌ Access Denied by Admin",
                        "timestamp": data["timestamp"]
                    }
                    st.session_state.is_locked = True
                    st.session_state.emergency_mode = True
                    # Sound the alarm
                    threading.Thread(target=sound_alarm, args=(2000, 1000)).start()
        except Exception as e:
            st.error(f"Error processing MQTT message: {str(e)}")

try:
    mqtt_client = MQTTClient()
    mqtt_client.client.loop_start()
except Exception as e:
    st.error(f"MQTT Error: {str(e)}")

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

class FaceRecognition:
    def __init__(self):
        self.mqtt_client = mqtt.Client("FaceRecognition")
        self.mqtt_client.connect("localhost", 1883)
        
    def recognize_face(self, face_img, recognized_name, is_recognized):
        timestamp = datetime.datetime.now().isoformat()
        if is_recognized:
            self.mqtt_client.publish("smartlock/access", 
                json.dumps({
                    "type": "access",
                    "authorized": True,
                    "user": recognized_name,
                    "timestamp": timestamp
                })
            )
            # Update lock status
            st.session_state.is_locked = False
        else:
            self.mqtt_client.publish("smartlock/access", 
                json.dumps({
                    "type": "access",
                    "authorized": False,
                    "user": "Unknown",
                    "timestamp": timestamp
                })
            )
            # Keep lock status locked
            st.session_state.is_locked = True
        
    def cleanup(self):
        self.mqtt_client.disconnect()

face_recognition = FaceRecognition()

def main():
    st.title("Smart Lock System")
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

    # Display lock status in the UI
    if st.session_state.is_locked:
        col2.error("🔒 DOOR LOCKED")
    else:
        col2.success("🔓 DOOR UNLOCKED")
        
    # Display emergency mode warning if active
    if st.session_state.emergency_mode:
        st.error("⚠️ EMERGENCY MODE ACTIVE - Security has been notified")

    if st.session_state.camera_running:
        cap = cv2.VideoCapture(0)
        while st.session_state.camera_running:
            ret, frame = cap.read()
            if not ret:
                st.warning("Unable to access webcam.")
                break

            # Publish the frame over MQTT for admin_control.py to use
            try:
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                mqtt_client.client.publish("smartlock/camera", jpg_as_text)
            except Exception as e:
                print(f"Error publishing camera frame: {e}")

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            recognized_name = None
            is_recognized = False
            for (x, y, w, h) in faces:
                size = max(w, h)
                center_x, center_y = x + w//2, y + h//2
                x_new = max(center_x - size//2, 0)
                y_new = max(center_y - size//2, 0)
                x_new = min(x_new, gray.shape[1] - size)
                y_new = min(y_new, gray.shape[0] - size)

                face_roi = gray[y_new:y_new + size, x_new:x_new + size]
                try:
                    label, confidence = recognizer.predict(face_roi)
                    if confidence < 70 and label in label_map:
                        recognized_name = label_map[label]
                        is_recognized = True
                    else:
                        recognized_name = "Unknown"
                except:
                    recognized_name = "Unknown"

                cv2.rectangle(rgb_frame, (x_new, y_new), (x_new + size, y_new + size), (0, 255, 0), 2)
                cv2.putText(rgb_frame, recognized_name, (x_new, y_new - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            face_recognition.recognize_face(frame, recognized_name, is_recognized)

            camera_placeholder.image(rgb_frame, channels="RGB", use_container_width=True, caption="Live Camera Feed")
            
            # Check for admin actions first
            if st.session_state.admin_action:
                feedback_placeholder.empty()  # Clear previous messages
                if "Allowed" in st.session_state.admin_action["message"]:
                    feedback_placeholder.success(st.session_state.admin_action["message"])
                else:
                    feedback_placeholder.error(st.session_state.admin_action["message"])
                time.sleep(3)
                st.session_state.admin_action = None
            # Then check for face recognition messages
            elif recognized_name:
                if recognized_name != "Unknown":
                    feedback_placeholder.success(f"✅ Welcome, {recognized_name}!")
                    st.session_state.unknown_timeout_until = None
                else:
                    current_time = time.time()
                    if st.session_state.unknown_timeout_until is None:
                        feedback_placeholder.error("❌ Face not recognized - Contacting admin...")
                        st.session_state.unknown_timeout_until = current_time + 60  # 60 second timeout
                    elif current_time < st.session_state.unknown_timeout_until:
                        # Don't show error during timeout, show waiting message instead
                        remaining_time = int(st.session_state.unknown_timeout_until - current_time)
                        feedback_placeholder.warning(f"⏳ Waiting for admin response... ({remaining_time}s)")
                    else:
                        # Timeout expired, show error again
                        feedback_placeholder.error("❌ Face not recognized - Contacting admin...")
                        st.session_state.unknown_timeout_until = current_time + 60

            # Check for legacy admin message (keeping for compatibility)
            if st.session_state.admin_message:
                feedback_placeholder.empty()  # Clear previous messages
                if "Allowed" in st.session_state.admin_message:
                    feedback_placeholder.success(st.session_state.admin_message)
                else:
                    feedback_placeholder.error(st.session_state.admin_message)
                time.sleep(3)
                st.session_state.admin_message = None

            if st.session_state.last_access:
                access = st.session_state.last_access
                status = "✅ Granted" if access["status"] == "granted" else "❌ Denied"
                col2.markdown(f"""
                    **Last Access Attempt**
                    - Name: {access['name']}
                    - Status: {status}
                    - Time: {access['timestamp']}
                """)

            time.sleep(0.03)
        cap.release()
        face_recognition.cleanup()

if __name__ == "__main__":
    main()