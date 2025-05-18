import paho.mqtt.client as mqtt
import json
import datetime
import logging
import time
import threading

# Track last message times by type to avoid log overcrowding
last_message_times = {
    "unknown_user": 0,
    "authorized_user": 0,
    "admin_allow": 0,
    "admin_deny": 0,
    "auto_relock": 0
}
MESSAGE_INTERVAL = 60  # 1 minute interval for all log types
AUTO_RELOCK_DELAY = 3  # 3 seconds auto-relock delay

# Store active auto-relock timer
relock_timer = None

# Try to import LED control module if available
try:
    from led_control import LockLED
    led = LockLED()
    led_available = True
    print("LED control initialized in system logs")
except (ImportError, RuntimeError):
    led_available = False
    print("GPIO or LED control not available - running system logs without LED indicator")

# Try to import buzzer control module if available
try:
    from buzzer_control import AlarmBuzzer
    buzzer = AlarmBuzzer()
    buzzer_available = True
    print("Buzzer control initialized in system logs")
except (ImportError, RuntimeError):
    buzzer_available = False
    print("GPIO or buzzer control not available - running system logs without alarm")

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe("smartlock/access")
    client.subscribe("smartlock/system")
    client.subscribe("smartlock/control")

def auto_relock_door(client):
    """Automatically relock the door after delay period"""
    global relock_timer
    
    # Update LED - turn on for locked
    if led_available:
        led.set_locked()
    
    # Send lockdown command with system source
    client.publish("smartlock/control",
                 json.dumps({
                     "command": "auto_relock",
                     "source": "system",
                     "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                 }))
    
    # Clear the timer reference
    relock_timer = None
    
    # Log the auto-relock (with rate limiting)
    current_time = time.time()
    if current_time - last_message_times["auto_relock"] >= MESSAGE_INTERVAL:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"Door automatically locked at {timestamp}"
        logging.info(log_message)
        last_message_times["auto_relock"] = current_time

def schedule_auto_relock(client):
    """Schedule the door to automatically relock after delay"""
    global relock_timer
    
    # Cancel any existing timer
    if relock_timer is not None:
        relock_timer.cancel()
    
    # Create new timer
    relock_timer = threading.Timer(AUTO_RELOCK_DELAY, auto_relock_door, args=[client])
    relock_timer.daemon = True  # Make sure thread doesn't block program exit
    relock_timer.start()

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
        current_time = time.time()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if msg.topic == "smartlock/access" and data["type"] == "access":
            if data["authorized"]:
                # Apply rate limiting to authorized user logs
                if current_time - last_message_times["authorized_user"] >= MESSAGE_INTERVAL:
                    log_message = f"{data['user']} unlocked door at {timestamp}"
                    logging.info(log_message)
                    last_message_times["authorized_user"] = current_time
                
                # Update LED if available - turn off for unlocked
                if led_available:
                    led.set_unlocked()
                
                # Schedule auto-relock after delay
                schedule_auto_relock(client)
                
                # Republish as system event
                client.publish("smartlock/events", json.dumps({
                    "name": data['user'],
                    "status": "granted",
                    "timestamp": timestamp
                }))
            else:
                # Rate limiting for unknown user logs
                if current_time - last_message_times["unknown_user"] >= MESSAGE_INTERVAL:
                    log_message = f"Unknown user trying to access. Contacting admin. {timestamp}"
                    logging.info(log_message)
                    last_message_times["unknown_user"] = current_time
                    
                    # Ensure LED shows locked status
                    if led_available:
                        led.set_locked()
                    
                    # Republish as system event
                    client.publish("smartlock/events", json.dumps({
                        "name": "Unknown",
                        "status": "denied",
                        "timestamp": timestamp
                    }))
        
        elif msg.topic == "smartlock/control" and data.get("source") == "admin":
            # Log admin actions with rate limiting
            if data["command"] == "unlock":
                if current_time - last_message_times["admin_allow"] >= MESSAGE_INTERVAL:
                    log_message = f"Unknown user allowed by admin at {timestamp}"
                    logging.info(log_message)
                    last_message_times["admin_allow"] = current_time
                
                # Update LED - turn off for unlocked
                if led_available:
                    led.set_unlocked()
                
                # Schedule auto-relock after delay
                schedule_auto_relock(client)
                
                # Send notification to face recognition app
                client.publish("smartlock/admin_action", json.dumps({
                    "action": "allowed",
                    "message": "Allowed by admin.",
                    "timestamp": timestamp
                }))
                
                # Log as event
                client.publish("smartlock/events", json.dumps({
                    "name": "Unknown (Admin Override)",
                    "status": "granted",
                    "timestamp": timestamp
                }))
                
            elif data["command"] == "lockdown":
                if current_time - last_message_times["admin_deny"] >= MESSAGE_INTERVAL:
                    log_message = f"Unknown user denied by admin at {timestamp}"
                    logging.info(log_message)
                    last_message_times["admin_deny"] = current_time
                
                # Update LED - turn on for locked
                if led_available:
                    led.set_locked()
                
                # Sound the alarm buzzer if available
                if buzzer_available:
                    # Sound for 10 seconds with rapid beeping
                    buzzer.sound_alarm(pattern=[(0.2, 0.2)], duration=10)
                
                # Send notification to face recognition app with emergency message
                client.publish("smartlock/admin_action", json.dumps({
                    "action": "denied",
                    "message": "Denied by admin. Contacting emergency services.",
                    "timestamp": timestamp
                }))
                
                # Log as event
                client.publish("smartlock/events", json.dumps({
                    "name": "Unknown (Admin Denied)",
                    "status": "denied",
                    "timestamp": timestamp
                }))
        
        elif msg.topic == "smartlock/system" and data.get("type") == "log":
            # Log system messages (like user creation) without rate limiting
            logging.info(data["message"])
            
    except Exception as e:
        logging.error(f"Error processing message: {e}")

def start_logger():
    logging.basicConfig(
        filename='smartlock_access.log',
        level=logging.INFO,
        format='%(asctime)s - %(message)s'
    )
    
    client = mqtt.Client("SystemLogger")
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect("localhost", 1883)
    client.loop_start()

if __name__ == "__main__":
    start_logger()
    
    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down logger...")
        # Clean up on exit
        if led_available:
            led.cleanup()
        if buzzer_available:
            buzzer.cleanup()
        # Cancel any pending relock timer
        if relock_timer is not None:
            relock_timer.cancel()