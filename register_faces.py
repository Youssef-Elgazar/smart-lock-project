import cv2
import numpy as np
import os
import shutil
import logging
import threading
import tkinter as tk
from tkinter import font as tkFont
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

# ==================================================================
# Index:
#   - FACE REGISTER CLASS
#   - PROCESS CAMERA FRAMES
#   - DETECT FACES IN FRAME
#   - START FACE CAPTURE
#   - CAPTURE NEXT FACE
#   - TRAIN THE RECOGNIZER
#   - CLEAR ALL DATA
#   - EXIT CLEANLY
#   - RUN APP
# ==================================================================

# =========== FACE REGISTER CLASS ===========
class Face_Register:
    def __init__(self):
        print("Initializing Face Register...")

        # Face/frame counters
        self.current_frame_faces_cnt = 0
        self.existing_faces_cnt = 0
        self.ss_cnt = 0

        # Create main window
        self.win = tk.Tk()
        self.win.title("Face Register")
        self.win.geometry("1200x720")

        # ---- LEFT: Camera Feed ----
        self.frame_left_camera = tk.Frame(self.win)
        self.label = tk.Label(self.frame_left_camera)  # Label to show video frames
        self.label.pack()
        self.frame_left_camera.pack(side=tk.LEFT, padx=10, pady=10)

        # ---- RIGHT: Controls ----
        self.frame_right_info = tk.Frame(self.win)

        # Title
        tk.Label(self.frame_right_info, text="Face Register", font=("Arial", 16, "bold")).pack(pady=10)

        # Input field for name
        tk.Label(self.frame_right_info, text="Enter Name:").pack()
        self.input_name = tk.Entry(self.frame_right_info, font=("Arial", 12))
        self.input_name.pack(pady=5)

        # Buttons
        tk.Button(self.frame_right_info, text="Capture Face", command=self.capture_multiple_faces, font=("Arial", 12), bg="green", fg="white").pack(pady=5)
        tk.Button(self.frame_right_info, text="Clear Data", command=self.clear_data, font=("Arial", 12), bg="red", fg="white").pack(pady=5)
        tk.Button(self.frame_right_info, text="Exit", command=self.exit_program, font=("Arial", 12), bg="gray", fg="white").pack(pady=5)

        # Status label and progress bar
        self.capture_label = tk.Label(self.frame_right_info, text="", font=("Arial", 14, "bold"))
        self.capture_label.pack(pady=10)
        self.progress_bar = ttk.Progressbar(self.frame_right_info, orient="horizontal", length=200, mode="determinate", maximum=20)
        self.progress_bar.pack(pady=5)

        # Face preview
        self.face_preview = tk.Label(self.frame_right_info)
        self.face_preview.pack(pady=5)

        self.frame_right_info.pack(side=tk.RIGHT, padx=10, pady=10)

        # ---- CAMERA SETUP ----
        self.cap = cv2.VideoCapture(0)
        # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))

        if not self.cap.isOpened():
            messagebox.showerror("Error", "Camera not detected. Please check your webcam.")
            return

        # Load Haar cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        self.process()  # Start frame processing loop

    # =========== PROCESS CAMERA FRAMES ===========
    def process(self):
        ret, frame = self.cap.read()
        if not ret or frame is None:
            print("Warning: Invalid frame received. Skipping...")
            self.win.after(3, self.process)
            return

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except cv2.error:
            print("Warning: Corrupt frame detected. Skipping...")
            self.win.after(3, self.process)
            return

        # Run face detection in a separate thread
        threading.Thread(target=self.detect_faces, args=(gray, frame)).start()

        # Show video frame in UI
        img = Image.fromarray(rgb_frame)
        img_tk = ImageTk.PhotoImage(image=img)
        self.label.img_tk = img_tk
        self.label.configure(image=img_tk)

        self.win.after(3, self.process)

    # =========== DETECT FACES IN FRAME ===========
    def detect_faces(self, gray_frame, frame):
        if self.ss_cnt % 5 == 0:
            faces = self.face_cascade.detectMultiScale(
                gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
        else:
            faces = []

        # Draw rectangles for debugging
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        self.ss_cnt += 1

    # =========== START FACE CAPTURE ===========
    def capture_multiple_faces(self):
        name = self.input_name.get().strip()

        if not name:
            messagebox.showerror("Error", "Please enter a name before capturing.")
            return

        self.capture_name = name
        self.capture_index = 1
        self.total_captures = 20  # Total images to collect

        # Create folders
        face_dir = "data/data_faces_from_camera"
        self.person_dir = os.path.join(face_dir, self.capture_name)
        os.makedirs(face_dir, exist_ok=True)
        os.makedirs(self.person_dir, exist_ok=True)

        # Reset UI elements
        self.capture_label.config(text="")
        self.progress_bar["value"] = 0
        self.face_preview.configure(image='')

        self.capture_next_image()  # Start capture loop

    # =========== CAPTURE NEXT FACE ===========
    def capture_next_image(self):
        if self.capture_index > self.total_captures:
            self.capture_label.config(text="✅ Capture complete!")
            self.train_recognizer()
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.capture_label.config(text="❌ Failed to capture image.")
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        if len(faces) == 0:
            self.capture_label.config(text=f"❗ No face detected [{self.capture_index}/{self.total_captures}]")
        else:
            for (x, y, w, h) in faces:
                # Save face image
                face_img = gray[y:y+h, x:x+w]
                filename = os.path.join(self.person_dir, f"face_{self.capture_index}.jpg")
                cv2.imwrite(filename, face_img)
                print(f"[{self.capture_index}/{self.total_captures}] Saved: {filename}")

                # Update UI
                self.capture_label.config(text=f"📸 Captured {self.capture_index}/{self.total_captures}")
                self.progress_bar["value"] = self.capture_index

                # Show preview
                face_preview_img = cv2.resize(face_img, (100, 100))
                face_preview_img = cv2.cvtColor(face_preview_img, cv2.COLOR_GRAY2RGB)
                img_tk = ImageTk.PhotoImage(image=Image.fromarray(face_preview_img))
                self.face_preview.img_tk = img_tk
                self.face_preview.configure(image=img_tk)

        self.win.after(500, self.capture_next_image)

    # =========== TRAIN THE RECOGNIZER ===========
    def train_recognizer(self):
        # Get face images and labels
        face_dir = "data/data_faces_from_camera"
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        faces = []
        labels = []
        label_ids = {}
        current_id = 0

        for person_dir in os.listdir(face_dir):
            person_path = os.path.join(face_dir, person_dir)
            if not os.path.isdir(person_path):
                continue  # Skip if not a directory

            label_ids[person_dir] = current_id
            current_id += 1

            for file in os.listdir(person_path):
                if not file.endswith((".png", ".jpg", ".jpeg")):
                    continue  # Skip non-image files
                path = os.path.join(person_path, file)
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                faces.append(img)
                labels.append(label_ids[person_dir])

        if len(faces) > 0:
            recognizer.train(faces, np.array(labels))
            recognizer.save("data/trained_model.yml")

            # Save label-to-ID mapping
            with open("data/label_mapping.txt", "w") as f:
                for name, id in label_ids.items():
                    f.write(f"{name},{id}\n")

            print("✅ Face recognizer trained successfully!")
        else:
            print("⚠️ No faces found for training!")

    # ====================== CLEAR ALL DATA ======================
    def clear_data(self):
        face_dir = "data/data_faces_from_camera/"
        if os.path.exists(face_dir):
            shutil.rmtree(face_dir)
            os.makedirs(face_dir)

            if os.path.exists("data/trained_model.yml"):
                os.remove("data/trained_model.yml")
            if os.path.exists("data/label_mapping.txt"):
                os.remove("data/label_mapping.txt")

            messagebox.showinfo("Success", "All face data has been cleared.")
        else:
            messagebox.showinfo("Info", "No face data to clear.")

    # ====================== EXIT CLEANLY ======================
    def exit_program(self):
        self.cap.release()
        cv2.destroyAllWindows()
        self.win.quit()

# ========================== RUN APP ==========================
def main():
    logging.basicConfig(level=logging.INFO)
    app = Face_Register()
    app.win.mainloop()

if __name__ == "__main__":
    main()