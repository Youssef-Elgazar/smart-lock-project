import paho.mqtt.client as mqtt
import json

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe("#")  # Subscribe to ALL topics
    print("Subscribed to all topics (#)")
    print("\n" + "="*60)
    print("Listening for MQTT messages...")
    print("="*60 + "\n")

def on_message(client, userdata, msg):
    print(f"\n{'='*60}")
    print(f"Topic: {msg.topic}")
    print(f"QoS: {msg.qos}")
    print(f"Payload length: {len(msg.payload)} bytes")
    
    try:
        # Try to decode as JSON
        data = json.loads(msg.payload)
        print(f"JSON Data: {json.dumps(data, indent=2)}")
    except:
        # If not JSON, show raw payload
        try:
            print(f"Text Payload: {msg.payload.decode('utf-8')[:200]}")
        except:
            print(f"Binary Payload: {msg.payload[:100]}")
    
    print(f"{'='*60}\n")

if __name__ == "__main__":
    client = mqtt.Client("DebugListener")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect("localhost", 1883)
        print("Connecting to MQTT broker at localhost:1883...")
        
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\nStopping debug listener...")
        client.disconnect()
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure Mosquitto MQTT broker is running!")