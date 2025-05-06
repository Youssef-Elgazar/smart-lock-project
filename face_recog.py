# face_recog.py
import tkinter as tk
from tkinter import messagebox, ttk
import cv2
import numpy as np
import os
import sqlite3
import datetime
import paho.mqtt.client as mqtt
import json

class FaceRecognizer:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.system_locked = False
        
        # MQTT Setup
        self.mqtt_client = mqtt.Client("FaceRecognizer")
        self.mqtt_client.connect("localhost", 1883)
        self.mqtt_client.subscribe("smartlock/control")
        self.mqtt_client.message_callback_add("smartlock/control", self.on_control_message)
        self.mqtt_client.loop_start()

        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        if os.path.exists("data/trained_model.yml"):
            self.recognizer.read("data/trained_model.yml")

        self.label_map = {}
        if os.path.exists("data/label_mapping.txt"):
            with open("data/label_mapping.txt", "r") as f:
                for line in f:
                    name, id = line.strip().split(',')
                    self.label_map[int(id)] = name

        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        self.cap = cv2.VideoCapture(0)
        self.frame_width = 640
        self.frame_height = 480
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

        if not self.cap.isOpened():
            messagebox.showerror("Error", "Camera not detected. Please check your webcam.")
            return

        self.recently_marked = {}
        self.re_mark_delay = 60
        self.marked_students = set()

        cv2.namedWindow("Face Recognition", cv2.WINDOW_NORMAL)

    def on_control_message(self, client, userdata, msg):
        command = json.loads(msg.payload)
        if command["command"] == "lockdown":
            self.system_locked = True
            print("SYSTEM LOCKDOWN ACTIVATED")
        elif command["command"] == "unlock":
            self.system_locked = False

    def mark_attendance(self, name):
        if self.system_locked or name == "Unknown":
            return

        now = datetime.datetime.now()
        if name in self.recently_marked:
            elapsed = (now - self.recently_marked[name]).total_seconds()
            if elapsed < self.re_mark_delay:
                return

        self.recently_marked[name] = now
        current_date = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M:%S')

        conn = sqlite3.connect("attendance.db")
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM attendance WHERE name = ? AND date = ?", (name, current_date))
        already_marked = cursor.fetchone()

        if not already_marked:
            cursor.execute("INSERT INTO attendance (name, time, date) VALUES (?, ?, ?)", (name, current_time, current_date))
            conn.commit()
            self.mqtt_client.publish("smartlock/events",
                                   json.dumps({
                                       "type": "access",
                                       "name": name,
                                       "status": "granted",
                                       "timestamp": now.isoformat()
                                   }))

        conn.close()
        self.marked_students.add(name)

    def detect_faces(self, gray_frame, frame):
      # Detect faces in grayscale frame
      faces = self.face_cascade.detectMultiScale(
        gray_frame,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
      )

      for (x, y, w, h) in faces:
        size = max(w, h)
        center_x, center_y = x + w // 2, y + h // 2
        x_new = max(center_x - size // 2, 0)
        y_new = max(center_y - size // 2, 0)
        x_new = min(x_new, gray_frame.shape[1] - size)
        y_new = min(y_new, gray_frame.shape[0] - size)

        face_roi = gray_frame[y_new:y_new + size, x_new:x_new + size]

        # Predict identity
        if hasattr(self.recognizer, 'predict'):
          try:
            label, confidence = self.recognizer.predict(face_roi)
            name = self.label_map[label] if confidence < 80 and label in self.label_map else "Unknown"
          except:
            name = "Unknown"
        else:
          name = "Unknown (Model not loaded)"

        self.mark_attendance(name)

        # Draw rectangle and name on frame
        cv2.rectangle(frame, (x_new, y_new), (x_new + size, y_new + size), (0, 255, 0), 2)
        cv2.putText(frame, name, (x_new, y_new - 10), self.font, 0.8, (0, 255, 0), 2)

    def draw_marked_names_panel(self, frame):
      # Create a right-side panel showing marked names
      height, width, _ = frame.shape
      panel_width = 300
      panel = np.zeros((height, panel_width, 3), dtype=np.uint8)
      panel[:] = (50, 50, 50)  # Dark gray background

      cv2.putText(panel, "Marked Present", (10, 30), self.font, 0.8, (255, 255, 255), 2)

      y_offset = 60
      for i, name in enumerate(sorted(self.marked_students)):
        cv2.putText(panel, f"{i+1}. {name}", (10, y_offset), self.font, 0.6, (0, 255, 255), 1)
        y_offset += 25
        if y_offset > height - 20:
          cv2.putText(panel, "...", (10, y_offset), self.font, 0.6, (200, 200, 200), 1)
          break

      return np.hstack((frame, panel))

    def run(self):
      # Main loop for webcam and face recognition
      while self.cap.isOpened():
        ret, frame = self.cap.read()
        if not ret or frame is None or frame.size == 0:
          print("Warning: Invalid frame received. Skipping...")
          continue

        try:
          gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        except cv2.error:
          print("Warning: Corrupt frame detected. Skipping...")
          continue

        self.detect_faces(gray, frame)

        # Display subject name and attendance count
        present_count = len(self.marked_students)
        # cv2.putText(frame, f"Subject: {self.subject}", (20, 40), self.font, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Present: {present_count}", (20, 80), self.font, 1, (0, 255, 255), 2)

        # Add name panel
        full_frame = self.draw_marked_names_panel(frame)
        cv2.imshow("Face Recognition", full_frame)

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
          break

      # Clean up
      self.cap.release()
      cv2.destroyAllWindows()

# =========== RUN APP ===========

if __name__ == "__main__":
  app = FaceRecognizer()
  app.run()