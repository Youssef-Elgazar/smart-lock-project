# admin_control.py
import tkinter as tk
from tkinter import messagebox, ttk
import cv2
from PIL import Image, ImageTk

class AdminControlPanel:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Admin Control Panel")
        self.window.geometry("1200x720")
        
        # Left side - Camera Feed
        self.camera_frame = tk.Frame(self.window, width=800, height=720)
        self.camera_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.camera_label = tk.Label(self.camera_frame)
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        
        # Right side - Control Buttons
        self.control_frame = tk.Frame(self.window, width=400, height=720, bg="#f0f0f0")
        self.control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        
        # Title
        tk.Label(self.control_frame, text="Admin Controls", font=("Arial", 24, "bold"), bg="#f0f0f0").pack(pady=40)
        
        # Accept Button (Green)
        self.accept_btn = tk.Button(
            self.control_frame, 
            text="ACCEPT", 
            command=self.accept_action,
            font=("Arial", 18, "bold"),
            bg="#4CAF50",  # Green
            fg="white",
            width=20,
            height=3
        )
        self.accept_btn.pack(pady=30)
        
        # Emergency Button (Red)
        self.emergency_btn = tk.Button(
            self.control_frame, 
            text="EMERGENCY", 
            command=self.emergency_action,
            font=("Arial", 18, "bold"),
            bg="#F44336",  # Red
            fg="white",
            width=20,
            height=3
        )
        self.emergency_btn.pack(pady=30)
        
        # Status Label
        self.status_label = tk.Label(
            self.control_frame, 
            text="System Ready", 
            font=("Arial", 14),
            bg="#f0f0f0"
        )
        self.status_label.pack(pady=20)
        
        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open video device")
            self.window.destroy()
            return
        
        self.update_camera()
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()
    
    def update_camera(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.imgtk = imgtk
            self.camera_label.configure(image=imgtk)
        self.window.after(10, self.update_camera)
    
    def accept_action(self):
        self.status_label.config(text="Accepted - System Active", fg="green")
        # Add your accept logic here
        print("Accept button pressed")
    
    def emergency_action(self):
        self.status_label.config(text="EMERGENCY - System Locked", fg="red")
        # Add your emergency logic here
        print("Emergency button pressed")
        messagebox.showwarning("Emergency", "Emergency protocol activated! System locked down.")
    
    def on_close(self):
        if self.cap.isOpened():
            self.cap.release()
        self.window.destroy()

if __name__ == "__main__":
    AdminControlPanel()
    