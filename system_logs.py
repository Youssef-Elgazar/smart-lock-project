import paho.mqtt.client as mqtt
import json
import datetime
import logging
import time

# Track last time unknown user message was logged
last_unknown_log_time = 0
UNKNOWN_LOG_INTERVAL = 60  # 60 seconds interval

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe("smartlock/access")
    client.subscribe("smartlock/system")
    client.subscribe("smartlock/control")

def on_message(client, userdata, msg):
    global last_unknown_log_time
    
    try:
        data = json.loads(msg.payload)
        current_time = time.time()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if msg.topic == "smartlock/access" and data["type"] == "access":
            if data["authorized"]:
                log_message = f"{data['user']} unlocked door at {timestamp}"
                logging.info(log_message)
                
                # Republish as system event
                client.publish("smartlock/events", json.dumps({
                    "name": data['user'],
                    "status": "granted",
                    "timestamp": timestamp
                }))
            else:
                # Only log unknown user message once per minute
                if current_time - last_unknown_log_time >= UNKNOWN_LOG_INTERVAL:
                    log_message = f"Unknown user trying to access. Contacting admin. {timestamp}"
                    logging.info(log_message)
                    last_unknown_log_time = current_time
                    
                    # Republish as system event
                    client.publish("smartlock/events", json.dumps({
                        "name": "Unknown",
                        "status": "denied",
                        "timestamp": timestamp
                    }))
        
        elif msg.topic == "smartlock/control" and data.get("source") == "admin":
            # Log admin actions
            if data["command"] == "unlock":
                log_message = f"Unknown user allowed by admin at {timestamp}"
                logging.info(log_message)
                
                # Send notification to face recognition app
                client.publish("smartlock/admin_action", json.dumps({
                    "action": "allowed",
                    "timestamp": timestamp
                }))
                
                # Log as event
                client.publish("smartlock/events", json.dumps({
                    "name": "Unknown (Admin Override)",
                    "status": "granted",
                    "timestamp": timestamp
                }))
                
            elif data["command"] == "lockdown":
                log_message = f"Unknown user denied by admin at {timestamp}"
                logging.info(log_message)
                
                # Send notification to face recognition app
                client.publish("smartlock/admin_action", json.dumps({
                    "action": "denied",
                    "timestamp": timestamp
                }))
                
                # Log as event
                client.publish("smartlock/events", json.dumps({
                    "name": "Unknown (Admin Denied)",
                    "status": "denied",
                    "timestamp": timestamp
                }))
        
        elif msg.topic == "smartlock/system" and data.get("type") == "log":
            # Log system messages (like user creation)
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