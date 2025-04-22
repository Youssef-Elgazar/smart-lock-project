import tkinter as tk
from tkinter import messagebox, ttk
import cv2
import numpy as np
import os
import sqlite3
import datetime

# ======================== DATABASE SETUP ============================
# Create the attendance database and necessary tables if they don't exist

conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# Create table for subjects with professor email
# cursor.execute("""
# 		CREATE TABLE IF NOT EXISTS subjects (
# 				name TEXT UNIQUE,
# 				email TEXT
# 		)
# """)

# Create table for storing attendance records
cursor.execute("""
		CREATE TABLE IF NOT EXISTS attendance (
				name TEXT, time TEXT, date TEXT,
				UNIQUE(name, date)
		)
""")

conn.commit()
conn.close()

# ======================== SUBJECT SELECTION GUI ============================

# class SubjectSelector:
# 		def __init__(self, root):
# 				self.root = root
# 				self.root.title("Select Subject")
# 				self.root.geometry("400x250")
# 				self.root.configure(bg="#f0f0f0")

# 				# Label and dropdown to choose subject
# 				tk.Label(root, text="Select Subject:", font=("Arial", 12), bg="#f0f0f0").pack(pady=10)
# 				self.subject_var = tk.StringVar(root)
# 				self.subjects = self.load_subjects()

# 				# if self.subjects:
# 				# 		self.subject_var.set(self.subjects[0])
# 				# else:
# 				# 		self.subject_var.set("No subjects available")
# 				# 		self.subjects = ["No subjects available"]

# 				self.subject_dropdown = ttk.Combobox(root, textvariable=self.subject_var,
# 																						 values=self.subjects, state="readonly",
# 																						 font=("Arial", 10))
# 				self.subject_dropdown.pack(pady=10)

# 				# Button to launch face recognition window
# 				ttk.Button(root, text="Start Recognition", command=self.start_recognition).pack(pady=20)

# 		def load_subjects(self):
# 				# Fetch subject names from DB
# 				conn = sqlite3.connect("attendance.db")
# 				cursor = conn.cursor()
# 				cursor.execute("SELECT name FROM subjects")
# 				subjects = [row[0] for row in cursor.fetchall()]
# 				conn.close()
# 				return subjects

# 		def start_recognition(self):
# 				selected_subject = self.subject_var.get()
# 				# if selected_subject == "No subjects available" or not selected_subject:
# 				# 		messagebox.showwarning("Warning", "Please add subjects first using Manage Subjects.")
# 				# 		return

# 				# self.root.destroy()
# 				FaceRecognizer(selected_subject).run()

# ======================== FACE RECOGNITION CLASS ============================

class FaceRecognizer:
	def __init__(self):
			# self.root = root
			# self.root.title("Face Recognition")
			# self.root.geometry("1280x720")
			# self.root.configure(bg="#f0f0f0")
			self.font = cv2.FONT_HERSHEY_SIMPLEX

			# Load pre-trained face recognizer
			self.recognizer = cv2.face.LBPHFaceRecognizer_create()
			if os.path.exists("modules/data/trained_model.yml"):
					self.recognizer.read("modules/data/trained_model.yml")

			# Load label map (id-to-name)
			self.label_map = {}
			if os.path.exists("modules/data/label_mapping.txt"):
					with open("modules/data/label_mapping.txt", "r") as f:
							for line in f:
									name, id = line.strip().split(',')
									self.label_map[int(id)] = name

			# Load Haar cascade for face detection
			self.face_cascade = cv2.CascadeClassifier(
					cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

			# Initialize webcam
			self.cap = cv2.VideoCapture(0)
			# self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
			self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
			self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

			# Check camera availability
			if not self.cap.isOpened():
					messagebox.showerror("Error", "Camera not detected. Please check your webcam.")
					return

			self.recently_marked = {}  # To avoid duplicate marking
			self.re_mark_delay = 60    # Re-mark delay in seconds
			self.marked_students = set()  # Names marked in this session

	def mark_attendance(self, name):
			# Avoid marking "Unknown"
			if name == "Unknown":
					return

			now = datetime.datetime.now()

			# Prevent duplicate marking within the re_mark_delay
			if name in self.recently_marked:
					elapsed = (now - self.recently_marked[name]).total_seconds()
					if elapsed < self.re_mark_delay:
							return

			self.recently_marked[name] = now
			current_date = now.strftime('%Y-%m-%d')
			current_time = now.strftime('%H:%M:%S')

			conn = sqlite3.connect("attendance.db")
			cursor = conn.cursor()

			# Check if already marked for this subject and date
			cursor.execute("SELECT 1 FROM attendance WHERE name = ? AND date = ?", (name, current_date))
			already_marked = cursor.fetchone()

			if not already_marked:
					cursor.execute("INSERT INTO attendance (name, time, date) VALUES (?, ?, ?)", (name, current_time, current_date))
					conn.commit()
					print(f"{name} marked present at {current_time}")

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

# ======================== RUN APP ============================

if __name__ == "__main__":
	app = FaceRecognizer()
	app.run()
