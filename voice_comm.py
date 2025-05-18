import pyaudio
import socket
import threading
import numpy as np
import time
import wave
import paho.mqtt.client as mqtt
import json

class VoiceCommunication:
    def __init__(self, is_admin=False):
        self.is_admin = is_admin
        self.streaming = False
        self.socket = None
        self.receive_thread = None
        self.send_thread = None
        
        # Audio configuration
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        
        # PyAudio instance
        self.audio = pyaudio.PyAudio()
        
        # MQTT for signaling
        self.mqtt_client = mqtt.Client("VoiceComm_" + ("Admin" if is_admin else "Door"))
        try:
            self.mqtt_client.connect("localhost", 1883)
            self.mqtt_client.subscribe("smartlock/voice_comm")
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.loop_start()
            print("Voice comm MQTT connected")
        except Exception as e:
            print(f"MQTT connection failed: {str(e)}")
    
    def on_mqtt_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            if data["action"] == "start_voice_comm":
                # Start voice communication
                if not self.streaming:
                    if self.is_admin:
                        self.start_as_admin(data["ip"])
                    else:
                        self.start_as_door(data["admin_ip"])
            elif data["action"] == "stop_voice_comm":
                # Stop voice communication
                self.stop()
        except Exception as e:
            print(f"Error in voice comm MQTT message: {str(e)}")
    
    def start_as_admin(self, door_ip):
        """Admin initiates the voice communication"""
        self.streaming = True
        self.door_ip = door_ip
        
        # Start UDP socket for audio streaming
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Start audio stream
        self.input_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        self.output_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            output=True,
            frames_per_buffer=self.chunk
        )
        
        # Start threads for sending and receiving audio
        self.send_thread = threading.Thread(target=self._send_audio, args=(door_ip, 12345))
        self.receive_thread = threading.Thread(target=self._receive_audio, args=(12346,))
        
        self.send_thread.daemon = True
        self.receive_thread.daemon = True
        
        self.send_thread.start()
        self.receive_thread.start()
        
        print(f"Voice communication started with door at {door_ip}")
    
    def start_as_door(self, admin_ip):
        """Door device receives the voice communication request"""
        self.streaming = True
        self.admin_ip = admin_ip
        
        # Start UDP socket for audio streaming
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Start audio stream
        self.input_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        self.output_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            output=True,
            frames_per_buffer=self.chunk
        )
        
        # Start threads for sending and receiving audio
        self.send_thread = threading.Thread(target=self._send_audio, args=(admin_ip, 12346))
        self.receive_thread = threading.Thread(target=self._receive_audio, args=(12345,))
        
        self.send_thread.daemon = True
        self.receive_thread.daemon = True
        
        self.send_thread.start()
        self.receive_thread.start()
        
        print(f"Voice communication started with admin at {admin_ip}")
    
    def _send_audio(self, ip, port):
        """Send audio from microphone to the other party"""
        try:
            while self.streaming:
                data = self.input_stream.read(self.chunk, exception_on_overflow=False)
                self.socket.sendto(data, (ip, port))
        except Exception as e:
            print(f"Error sending audio: {str(e)}")
    
    def _receive_audio(self, port):
        """Receive audio from the other party and play it"""
        self.socket.bind(('0.0.0.0', port))
        
        try:
            while self.streaming:
                data, addr = self.socket.recvfrom(self.chunk * 4)
                self.output_stream.write(data)
        except Exception as e:
            print(f"Error receiving audio: {str(e)}")
    
    def stop(self):
        """Stop the voice communication"""
        if self.streaming:
            self.streaming = False
            
            # Stop threads
            if self.send_thread and self.send_thread.is_alive():
                self.send_thread.join(1.0)
            if self.receive_thread and self.receive_thread.is_alive():
                self.receive_thread.join(1.0)
            
            # Close audio streams
            if hasattr(self, 'input_stream'):
                self.input_stream.stop_stream()
                self.input_stream.close()
            
            if hasattr(self, 'output_stream'):
                self.output_stream.stop_stream()
                self.output_stream.close()
            
            # Close socket
            if self.socket:
                self.socket.close()
                self.socket = None
            
            print("Voice communication stopped")
    
    def cleanup(self):
        """Clean up resources"""
        self.stop()
        self.audio.terminate()
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        print("Voice communication resources cleaned up")