import paho.mqtt.client as mqtt
import json
import datetime
import time

# Test if we can publish to smartlock/access
client = mqtt.Client("TestPublisher")

try:
    client.connect("localhost", 1883)
    print("Connected to MQTT broker")
    
    # Publish a test authorized message
    test_message = json.dumps({
        "type": "access",
        "authorized": True,
        "user": "TestUser",
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    print(f"Publishing test message: {test_message}")
    client.publish("smartlock/access", test_message, qos=0)
    print("Test message published to smartlock/access")
    
    # Wait a moment
    time.sleep(2)
    
    # Publish a test unauthorized message
    test_message2 = json.dumps({
        "type": "access",
        "authorized": False,
        "user": "Unknown",
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    print(f"Publishing test message: {test_message2}")
    client.publish("smartlock/access", test_message2, qos=0)
    print("Test message published to smartlock/access")
    
    time.sleep(1)
    client.disconnect()
    print("\nTest complete. Check your system_logs.py output and smartlock_access.log file.")
    
except Exception as e:
    print(f"Error: {e}")
    print("Make sure Mosquitto MQTT broker is running!")
