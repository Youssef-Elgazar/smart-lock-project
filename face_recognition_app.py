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
import socket
# Add PiCamera2 imports
from picamera2 import Picamera2
try:
    from libcamera import controls
except ImportError:
    # Create a simple placeholder if the full module isn't available
    class ControlsPlaceholder:
        class AfModeEnum:
            Continuous = 2  # Default value, may not work on all cameras
    controls = ControlsPlaceholder()

# Import LED control with fallback for non-Raspberry Pi environments
try:
    from led_control import LockLED
    led_available = True
except (ImportError, RuntimeError):
    # When running on non-Raspberry Pi systems or when GPIO is not available
    print("GPIO or LED control not available - running in simulation mode")
    led_available = False

# Import buzzer control with fallback
try:
    from buzzer_control import AlarmBuzzer
    buzzer_available = True
except (ImportError, RuntimeError):
    print("Buzzer control not available - running without alarm")
    buzzer_available = False

# Import voice communication with fallback
try:
    from voice_comm import VoiceCommunication
    voice_comm_available = True
    print("Voice communication available")
except ImportError:
    voice_comm_available = False
    print("Voice communication not available - missing PyAudio or other dependencies")    

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
if 'relock_timer' not in st.session_state:
    st.session_state.relock_timer = None
if 'emergency_mode' not in st.session_state:
    st.session_state.emergency_mode = False
# Initialize session state for voice communication
if 'voice_active' not in st.session_state:
    st.session_state.voice_active = False
if 'voice_message' not in st.session_state:
    st.session_state.voice_message = None

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client(client_id="WebApp")
        
        try:
            self.client.connect("localhost", 1883)
            self.client.subscribe([
                ("smartlock/events", 0), 
                ("smartlock/control", 0),
                ("smartlock/admin_action", 0),  # Admin actions
                ("smartlock/voice_comm", 0)     # Voice communication commands
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
                        
                        # Update LED if available
                        if led_available and 'face_recognition' in globals() and hasattr(face_recognition, 'led'):
                            face_recognition.led.set_unlocked()
                            
                        # No need to start relock timer here since system_logs.py handles it
                    elif data["command"] == "lockdown":
                        st.session_state.admin_message = "❌ Access Denied by Admin"
                        st.session_state.is_locked = True
                        
                        # Update LED if available
                        if led_available and 'face_recognition' in globals() and hasattr(face_recognition, 'led'):
                            face_recognition.led.set_locked()
                        
                        # Activate buzzer if available
                        if buzzer_available and 'face_recognition' in globals() and hasattr(face_recognition, 'buzzer'):
                            face_recognition.buzzer.sound_alarm(duration=10)
                            
                        # Set emergency mode
                        st.session_state.emergency_mode = True
                    elif data["command"] == "auto_relock":
                        # Auto relock command
                        st.session_state.is_locked = True
                        
                        # Update LED if available
                        if led_available and 'face_recognition' in globals() and hasattr(face_recognition, 'led'):
                            face_recognition.led.set_locked()
            elif msg.topic == "smartlock/admin_action":
                # Handle admin actions from system_logs
                if data["action"] == "allowed":
                    st.session_state.admin_action = {
                        "message": data["message"] if "message" in data else "✅ Access Allowed by Admin",
                        "timestamp": data["timestamp"]
                    }
                    st.session_state.is_locked = False
                    
                    # Update LED if available
                    if led_available and 'face_recognition' in globals() and hasattr(face_recognition, 'led'):
                        face_recognition.led.set_unlocked()
                        
                    # Reset emergency mode if it was active
                    st.session_state.emergency_mode = False
                        
                elif data["action"] == "denied":
                    st.session_state.admin_action = {
                        "message": data["message"] if "message" in data else "❌ Access Denied by Admin",
                        "timestamp": data["timestamp"]
                    }
                    st.session_state.is_locked = True
                    
                    # Update LED if available
                    if led_available and 'face_recognition' in globals() and hasattr(face_recognition, 'led'):
                        face_recognition.led.set_locked()
                    
                    # Activate buzzer if available
                    if buzzer_available and 'face_recognition' in globals() and hasattr(face_recognition, 'buzzer'):
                        face_recognition.buzzer.sound_alarm(duration=10)
                    
                    # Set emergency mode
                    st.session_state.emergency_mode = True
            elif msg.topic == "smartlock/voice_comm":
                if voice_comm_available and 'face_recognition' in globals() and hasattr(face_recognition, 'voice_comm'):
                    try:
                        if data["action"] == "start_voice_comm":
                            # Start voice communication
                            admin_ip = data["admin_ip"]
                            st.session_state.voice_active = True
                            face_recognition.voice_comm.start_as_door(admin_ip)
                            
                            # Display intercom active message
                            st.session_state.voice_message = "📞 Intercom active - Admin is speaking"
                            
                        elif data["action"] == "stop_voice_comm":
                            # Stop voice communication
                            st.session_state.voice_active = False
                            face_recognition.voice_comm.stop()
                            
                            # Clear intercom message
                            st.session_state.voice_message = None
                    except Exception as e:
                        print(f"Error handling voice communication: {e}")
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
        
        # Initialize LED control if available (on Raspberry Pi)
        if led_available:
            self.led = LockLED()
            print("LED control initialized")
        else:
            self.led = None
            
        # Initialize buzzer control if available
        if buzzer_available:
            self.buzzer = AlarmBuzzer()
            print("Buzzer control initialized")
        else:
            self.buzzer = None
            
        # Initialize voice communication if available
        if voice_comm_available:
            try:
                self.voice_comm = VoiceCommunication(is_admin=False)
                print("Voice communication initialized for door")
            except Exception as e:
                print(f"Error initializing voice communication: {e}")
                self.voice_comm = None
        else:
            self.voice_comm = None
        
        # Auto-relock timer
        self.relock_timer = None
        
        # Get and publish local IP address
        self.local_ip = self.get_local_ip()
        self.publish_device_info()
        
    def get_local_ip(self):
        """Get the local IP address of this device"""
        try:
            # Create a socket and connect to an external server
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"  # Fallback to localhost

    def publish_device_info(self):
        """Publish the door device information"""
        self.mqtt_client.publish("smartlock/device_info", 
                               json.dumps({
                                   "type": "door",
                                   "ip": self.local_ip,
                                   "timestamp": datetime.datetime.now().isoformat()
                               }))
        
    def auto_relock(self):
        """Automatically relock the door after 3 seconds"""
        # Set door status back to locked
        st.session_state.is_locked = True
        
        # Update LED if available
        if self.led:
            self.led.set_locked()
            
        # Send relock message via MQTT
        self.mqtt_client.publish("smartlock/control", 
            json.dumps({
                "command": "auto_relock",
                "source": "system",
                "timestamp": datetime.datetime.now().isoformat()
            })
        )
        
        # Reset the timer
        self.relock_timer = None
        
    def recognize_face(self, face_img, recognized_name, is_recognized):
        timestamp = datetime.datetime.now().isoformat()
        if is_recognized:
            # Authorized user detected, unlock door
            self.mqtt_client.publish("smartlock/access", 
                json.dumps({
                    "type": "access",
                    "authorized": True,
                    "user": recognized_name,
                    "timestamp": timestamp
                })
            )
            # Update lock status and LED
            st.session_state.is_locked = False
            if self.led:
                self.led.set_unlocked()
                
            # Reset emergency mode if it was active
            st.session_state.emergency_mode = False
                
            # Buzzer - sound a confirmation beep
            if self.buzzer:
                self.buzzer.beep(0.1)  # Short confirmation beep
                
            # Schedule auto-relock after 3 seconds
            # We don't need to do it here because system_logs.py handles it
        else:
            # Unauthorized user, keep door locked
            self.mqtt_client.publish("smartlock/access", 
                json.dumps({
                    "type": "access",
                    "authorized": False,
                    "user": "Unknown",
                    "timestamp": timestamp
                })
            )
            # Keep lock status and LED in locked state
            st.session_state.is_locked = True
            if self.led:
                self.led.set_locked()
        
    def cleanup(self):
        # Clean up resources when exiting
        if self.led:
            self.led.cleanup()
        if self.buzzer:
            self.buzzer.cleanup()
        if hasattr(self, 'voice_comm') and self.voice_comm:
            self.voice_comm.cleanup()
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

    # Initialize PiCamera2 outside the loop, but only when needed
    picam2 = None
    
    # Display lock status in the UI
    if st.session_state.is_locked:
        col2.error("🔒 DOOR LOCKED")
    else:
        col2.success("🔓 DOOR UNLOCKED")
        
    # Display emergency mode warning if active
    if st.session_state.emergency_mode:
        st.error("⚠️ EMERGENCY MODE ACTIVE - Security has been notified")
        
    # Display voice communication status if active
    if st.session_state.voice_message:
        col2.info(st.session_state.voice_message)
    
    if st.session_state.camera_running:
        try:
            # Set up PiCamera2 instead of OpenCV VideoCapture
            picam2 = Picamera2()
            frame_width = 640
            frame_height = 480
            
            # Configure the camera
            config = picam2.create_preview_configuration(
                main={"size": (frame_width, frame_height), "format": "RGB888"}
            )
            picam2.configure(config)
            
            # Try to set autofocus if available
            try:
                picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
                print("Continuous autofocus enabled")
            except Exception as e:
                print(f"Autofocus not available: {e}")
                try:
                    picam2.set_controls({"LensPosition": 0.5})  # Mid-distance focus
                    print("Manual focus set")
                except:
                    print("Manual focus not available either")
            
            # Start the camera
            picam2.start()
            
            # Main camera loop
            while st.session_state.camera_running:
                # Capture frame from PiCamera2
                frame = picam2.capture_array()
                
                if frame is None or frame.size == 0:
                    st.warning("Unable to access camera.")
                    break

                # PiCamera2 gives RGB frames, but OpenCV expects BGR for processing
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Publish the frame over MQTT for admin_control.py to use
                try:
                    _, buffer = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 50])
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                    mqtt_client.client.publish("smartlock/camera", jpg_as_text)
                except Exception as e:
                    print(f"Error publishing camera frame: {e}")

                # For display, we can use the RGB frame directly from PiCamera2
                rgb_frame = frame.copy()  # Already in RGB format
                
                # For face detection, we need gray scale image from the BGR frame
                gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
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

                    # Draw rectangle and name on the RGB frame for display
                    cv2.rectangle(rgb_frame, (x_new, y_new), (x_new + size, y_new + size), (0, 255, 0), 2)
                    cv2.putText(rgb_frame, recognized_name, (x_new, y_new - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                face_recognition.recognize_face(frame_bgr, recognized_name, is_recognized)

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
                
            # Clean up camera resources when stopped
            if picam2:
                picam2.stop()
                
        except Exception as e:
            st.error(f"Camera error: {str(e)}")
            if picam2:
                picam2.stop()
            
        face_recognition.cleanup()

if __name__ == "__main__":
    main()