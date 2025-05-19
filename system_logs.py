import paho.mqtt.client as mqtt
import json
import datetime
import logging
import time

# Track last message times by type to avoid log overcrowding
last_message_times = {
    "unknown_user": 0,
    "authorized_user": 0,
    "admin_allow": 0,
    "admin_deny": 0,
    "system_log": 0
}
MESSAGE_INTERVAL = 60  # 1 minute interval for all log types

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe([
        ("smartlock/access", 2),  # Access events - QoS 2
        ("smartlock/system", 2),  # System logs - QoS 2
        ("smartlock/control", 2)   # Control commands - QoS 2
    ])

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
                
                # Republish as system event (no rate limiting for events)
                client.publish("smartlock/events", json.dumps({
                    "name": data['user'],
                    "status": "granted",
                    "timestamp": timestamp
                }), qos=2)  # Events - QoS 2
            else:
                # Rate limiting for unknown user logs
                if current_time - last_message_times["unknown_user"] >= MESSAGE_INTERVAL:
                    log_message = f"Unknown user trying to access. Contacting admin. {timestamp}"
                    logging.info(log_message)
                    last_message_times["unknown_user"] = current_time
                    
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
                
                # Send notification to face recognition app with custom message
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
            # Log system messages (like user creation) with rate limiting
            # Exception: Always log user creation messages
            if data["message"].startswith("User:") or current_time - last_message_times["system_log"] >= MESSAGE_INTERVAL:
                logging.info(data["message"])
                # Only update timestamp for non-user creation logs
                if not data["message"].startswith("User:"):
                    last_message_times["system_log"] = current_time
            
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