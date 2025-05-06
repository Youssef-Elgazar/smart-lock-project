import cv2
from picamera2 import Picamera2
# Initialize PiCamera2
picam2 = Picamera2()
picam2.preview_configuration.main.size = (640, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()
# Capture an image
frame = picam2.capture_array()
# Convert to OpenCV format
frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
# Save the image
cv2.imwrite("captured_image.jpg", frame)
print("Image saved as 'captured_image.jpg'")
picam2.close()
