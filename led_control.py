import RPi.GPIO as GPIO
import time

class LockLED:
    def __init__(self):
        # Set up GPIO mode
        GPIO.setmode(GPIO.BCM)
        
        # For Raspberry Pi, the built-in LED is typically GPIO 17
        # Some models use different pins - modify if needed for your specific model
        self.led_pin = 17
        
        # Set up the GPIO pin as output
        GPIO.setup(self.led_pin, GPIO.OUT)
        
        # Initialize to locked state (LED on)
        self.set_locked()
        
    def set_locked(self):
        """Turn LED on to indicate the door is locked"""
        GPIO.output(self.led_pin, GPIO.HIGH)
        print("LED ON - Door Locked")
        
    def set_unlocked(self):
        """Turn LED off to indicate the door is unlocked"""
        GPIO.output(self.led_pin, GPIO.LOW)
        print("LED OFF - Door Unlocked")
        
    def blink(self, times=3, interval=0.2):
        """Blink LED to indicate activity or transitions"""
        for _ in range(times):
            GPIO.output(self.led_pin, GPIO.HIGH)
            time.sleep(interval)
            GPIO.output(self.led_pin, GPIO.LOW)
            time.sleep(interval)
            
    def cleanup(self):
        """Clean up GPIO on exit"""
        GPIO.cleanup()