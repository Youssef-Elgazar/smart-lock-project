import RPi.GPIO as GPIO
import time
import threading

class AlarmBuzzer:
    def __init__(self):
        # Set up GPIO mode
        GPIO.setmode(GPIO.BCM)
        
        # Buzzer pin - modify if using a different GPIO pin
        self.buzzer_pin = 27
        
        # Set up the buzzer pin as output
        GPIO.setup(self.buzzer_pin, GPIO.OUT)
        
        # Initialize as off
        self.turn_off()
        
        # Track if alarm is active
        self.alarm_active = False
        self.alarm_thread = None
        
    def turn_on(self):
        """Turn buzzer on"""
        GPIO.output(self.buzzer_pin, GPIO.HIGH)
        print("BUZZER ON - Alarm activated")
        
    def turn_off(self):
        """Turn buzzer off"""
        GPIO.output(self.buzzer_pin, GPIO.LOW)
        print("BUZZER OFF - Alarm deactivated")
        
    def beep(self, duration=0.5):
        """Beep the buzzer once for specified duration"""
        self.turn_on()
        time.sleep(duration)
        self.turn_off()
        
    def sound_alarm(self, pattern=None, duration=10):
        """Sound alarm with pattern for specified duration
        pattern: List of (on_time, off_time) tuples in seconds
        """
        if self.alarm_active:
            return  # Don't start another alarm if one is already running
            
        # Default pattern: rapid beeps
        if pattern is None:
            pattern = [(0.2, 0.2)]  # 0.2s on, 0.2s off
            
        self.alarm_active = True
        
        # Start alarm in separate thread so it doesn't block
        self.alarm_thread = threading.Thread(
            target=self._alarm_sequence, 
            args=(pattern, duration)
        )
        self.alarm_thread.daemon = True
        self.alarm_thread.start()
        
    def _alarm_sequence(self, pattern, duration):
        """Internal method to run the alarm sequence"""
        start_time = time.time()
        try:
            while time.time() - start_time < duration and self.alarm_active:
                for on_time, off_time in pattern:
                    if not self.alarm_active:
                        break
                    self.turn_on()
                    time.sleep(on_time)
                    self.turn_off()
                    time.sleep(off_time)
        finally:
            self.turn_off()
            self.alarm_active = False
            
    def stop_alarm(self):
        """Stop currently running alarm"""
        self.alarm_active = False
        self.turn_off()
            
    def cleanup(self):
        """Clean up GPIO on exit"""
        self.stop_alarm()
        # Don't call GPIO.cleanup() here - it might affect other components
        # Just reset our specific pin
        GPIO.setup(self.buzzer_pin, GPIO.IN)