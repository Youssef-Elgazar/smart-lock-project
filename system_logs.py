import paho.mqtt.client as mqtt
import json
import datetime
import logging
import time

# Track last message times by type to avoid log overcrowding
last_message_times = {
    "unknown_user": 0,
    "admin_allow": 0,
    "admin_deny": 0,
    "system_log": 0
}
MESSAGE_INTERVAL = 60  # 1 minute interval for repeated unknown/admin logs

# Track last recognized user to avoid duplicate logs
last_recognized_user = None
last_recognized_time = 0
USER_LOG_COOLDOWN = 5  # Log same user only once every 5 seconds

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code: {rc}")
    if rc == 0:
        # Subscribe to each topic individually with QoS 0
        result1 = client.subscribe("smartlock/access", qos=0)
        result2 = client.subscribe("smartlock/system", qos=0)
        result3 = client.subscribe("smartlock/control", qos=0)
        print(f"Subscribed to smartlock/access: {result1}")
        print(f"Subscribed to smartlock/system: {result2}")
        print(f"Subscribed to smartlock/control: {result3}")
    else:
        print(f"Failed to connect with result code: {rc}")

def on_message(client, userdata, msg):
    global last_recognized_user, last_recognized_time
    
    try:
        data = json.loads(msg.payload)
        current_time = time.time()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if msg.topic == "smartlock/access" and data["type"] == "access":
            if data["authorized"]:
                # Log authorized user entry (with cooldown to prevent spam)
                user_name = data['user']
                if (user_name != last_recognized_user or 
                    current_time - last_recognized_time >= USER_LOG_COOLDOWN):
                    log_message = f"{user_name} entered at {timestamp}"
                    logging.info(log_message)
                    print(f"Logged: {log_message}")
                    last_recognized_user = user_name
                    last_recognized_time = current_time
                
                # Republish as system event
                client.publish("smartlock/events", json.dumps({
                    "name": data['user'],
                    "status": "granted",
                    "timestamp": timestamp
                }), qos=0)
            else:
                # Rate limiting for unknown user logs
                if current_time - last_message_times["unknown_user"] >= MESSAGE_INTERVAL:
                    log_message = f"Unknown user trying to access at {timestamp}"
                    logging.info(log_message)
                    print(f"Logged: {log_message}")
                    last_message_times["unknown_user"] = current_time
                    
                    # Republish as system event
                    client.publish("smartlock/events", json.dumps({
                        "name": "Unknown",
                        "status": "denied",
                        "timestamp": timestamp
                    }), qos=0)
        
        elif msg.topic == "smartlock/control" and data.get("source") == "admin":
            # Log admin actions with rate limiting
            if data["command"] == "unlock":
                if current_time - last_message_times["admin_allow"] >= MESSAGE_INTERVAL:
                    log_message = f"Unknown user allowed by admin at {timestamp}"
                    logging.info(log_message)
                    print(f"Logged: {log_message}")
                    last_message_times["admin_allow"] = current_time
                
                # Send notification to face recognition app
                client.publish("smartlock/admin_action", json.dumps({
                    "action": "allowed",
                    "message": "Allowed by admin.",
                    "timestamp": timestamp
                }), qos=0)
                
                # Log as event
                client.publish("smartlock/events", json.dumps({
                    "name": "Unknown (Admin Override)",
                    "status": "granted",
                    "timestamp": timestamp
                }), qos=0)
                
            elif data["command"] == "lockdown":
                if current_time - last_message_times["admin_deny"] >= MESSAGE_INTERVAL:
                    log_message = f"Unknown user denied by admin at {timestamp}"
                    logging.info(log_message)
                    print(f"Logged: {log_message}")
                    last_message_times["admin_deny"] = current_time
                
                # Send notification to face recognition app
                client.publish("smartlock/admin_action", json.dumps({
                    "action": "denied",
                    "message": "Denied by admin. Contacting emergency services.",
                    "timestamp": timestamp
                }), qos=0)
                
                # Log as event
                client.publish("smartlock/events", json.dumps({
                    "name": "Unknown (Admin Denied)",
                    "status": "denied",
                    "timestamp": timestamp
                }), qos=0)
        
        elif msg.topic == "smartlock/system" and data.get("type") == "log":
            # Log system messages (like user creation)
            if data["message"].startswith("User:") or current_time - last_message_times["system_log"] >= MESSAGE_INTERVAL:
                logging.info(data["message"])
                print(f"Logged: {data['message']}")
                if not data["message"].startswith("User:"):
                    last_message_times["system_log"] = current_time
            
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        print(f"Error: {e}")

def start_logger():
    logging.basicConfig(
        filename='smartlock_access.log',
        level=logging.INFO,
        format='%(asctime)s - %(message)s'
    )
    
    print("System Logger started. Monitoring MQTT topics...")
    print(f"Logging to: smartlock_access.log")
    
    client = mqtt.Client("SystemLogger")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect("localhost", 1883)
        client.loop_start()
        print("Successfully connected to MQTT broker")
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        return None
    
    return client

if __name__ == "__main__":
    client = start_logger()
    
    if client:
        try:
            print("\nPress Ctrl+C to stop the logger\n")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down logger...")
            client.disconnect()
    else:
        print("Logger failed to start")