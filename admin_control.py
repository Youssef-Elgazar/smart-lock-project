# admin_control.py
import tkinter as tk
from tkinter import messagebox, ttk
import cv2
from PIL import Image, ImageTk
import paho.mqtt.client as mqtt
import json
import base64
import numpy as np
import time
import datetime

class AdminControlPanel:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Admin Control Panel")
        self.window.geometry("1200x720")
        
        # Flag to track if we've received camera frames yet
        self.received_frame = False
        
        # MQTT Client Setup with updated client initialization
        self.mqtt_client = mqtt.Client(client_id="AdminPanel")
        try:
            self.mqtt_client.connect("localhost", 1883)
            self.mqtt_client.subscribe("smartlock/camera")  # Subscribe to camera feed
            self.mqtt_client.on_message = self.on_message
            self.mqtt_client.loop_start()
            print("Connected to MQTT broker")
        except ConnectionRefusedError:
            messagebox.showerror("MQTT Error", "Failed to connect to MQTT broker. Is Mosquitto running?")
            print("Failed to connect to MQTT broker. Is Mosquitto running?")
        
        # Left side - Camera Feed
        self.camera_frame = tk.Frame(self.window, width=800, height=720)
        self.camera_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.camera_label = tk.Label(self.camera_frame)
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        
        # Right side - Controls
        self.control_frame = tk.Frame(self.window, width=400, height=720, bg="#f0f0f0")
        self.control_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        
        tk.Label(self.control_frame, text="Admin Controls", font=("Arial", 24, "bold"), bg="#f0f0f0").pack(pady=40)
        
        self.accept_btn = tk.Button(
            self.control_frame, 
            text="ALLOW ACCESS", 
            command=self.accept_action,
            font=("Arial", 18, "bold"),
            bg="#4CAF50",
            fg="white",
            width=20,
            height=3
        )
        self.accept_btn.pack(pady=30)
        
        self.deny_btn = tk.Button(
            self.control_frame, 
            text="DENY ACCESS", 
            command=self.deny_action,
            font=("Arial", 18, "bold"),
            bg="#F44336",
            fg="white",
            width=20,
            height=3
        )
        self.deny_btn.pack(pady=30)
        
        self.status_label = tk.Label(
            self.control_frame, 
            text="System Ready", 
            font=("Arial", 14),
            bg="#f0f0f0"
        )
        self.status_label.pack(pady=20)
        
        # Connection status indicator
        self.connection_status = tk.Label(
            self.control_frame,
            text="Waiting for camera feed...",
            font=("Arial", 12),
            bg="#f0f0f0",
            fg="orange"
        )
        self.connection_status.pack(pady=10)
        
        # Add a placeholder message in the camera area
        self.camera_label.config(text="Waiting for camera feed from face recognition app...", 
                                font=("Arial", 14))
        
        # Schedule a check for camera feed
        self.window.after(5000, self.check_camera_feed)
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()
    
    def check_camera_feed(self):
        """Check if we've received any camera frames after 5 seconds"""
        if not self.received_frame:
            self.connection_status.config(
                text="No camera feed received. Is face_recognition_app.py running?",
                fg="red"
            )
        self.window.after(5000, self.check_camera_feed)
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        if msg.topic == "smartlock/camera":
            try:
                # Decode the image from base64
                jpg_original = base64.b64decode(msg.payload)
                np_arr = np.frombuffer(jpg_original, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                # Convert to RGB for display
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_label.imgtk = imgtk
                self.camera_label.configure(image=imgtk)
                
                # Update connection status if this is the first frame
                if not self.received_frame:
                    self.received_frame = True
                    self.connection_status.config(
                        text="Connected to camera feed",
                        fg="green"
                    )
            except Exception as e:
                print(f"Error processing camera frame: {e}")
    
    def accept_action(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_label.config(text="Access Allowed - Door Unlocked", fg="green")
        
        # Send unlock command with admin source
        self.mqtt_client.publish("smartlock/control", 
                               json.dumps({"command": "unlock", "source": "admin"}))
        
        # Log the action
        self.mqtt_client.publish("smartlock/system",
                               json.dumps({
                                   "type": "log",
                                   "message": f"Unknown user allowed by admin at {timestamp}"
                               }))
        
        # Reset status after 3 seconds
        self.window.after(3000, lambda: self.status_label.config(text="System Ready", fg="black"))

    def deny_action(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_label.config(text="Access Denied - Door Locked", fg="red")
        
        # Send lockdown command with admin source
        self.mqtt_client.publish("smartlock/control",
                               json.dumps({"command": "lockdown", "source": "admin"}))
        
        # Log the action
        self.mqtt_client.publish("smartlock/system",
                               json.dumps({
                                   "type": "log",
                                   "message": f"Unknown user denied by admin at {timestamp}"
                               }))
        
        messagebox.showinfo("Access Denied", "Access has been denied. Door remains locked.")
        
        # Reset status after 3 seconds
        self.window.after(3000, lambda: self.status_label.config(text="System Ready", fg="black"))
    
    def on_close(self):
        self.mqtt_client.disconnect()
        self.window.destroy()

if __name__ == "__main__":
    AdminControlPanel()