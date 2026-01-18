import asyncio
from bleak import BleakClient
import paho.mqtt.client as mqtt

TRAIN_MAC = "XX:XX:XX:XX:XX:XX"  # Vervang met jouw MAC adres
CHAR_UUID = "00001624-1212-efde-1623-785feabcd123"

client_ble = None
current_speed = 0
loop = None
connected = False
mqtt_client = None

async def send_speed(speed):
    global client_ble, current_speed, connected
    if not connected or not client_ble:
        print("Niet verbonden")
        return False
    try:
        if speed < 0:
            speed_byte = 256 + speed
        else:
            speed_byte = int(speed)
        cmd = bytes([0x08, 0x00, 0x81, 0x00, 0x01, 0x51, 0x00, speed_byte])
        await client_ble.write_gatt_char(CHAR_UUID, cmd)
        current_speed = speed
        print(f"Motor snelheid: {speed}")
        return True
    except Exception as e:
        print(f"Fout: {e}")
        connected = False
        return False

def on_disconnect(client):
    global connected
    print("Verbinding verloren!")
    connected = False

def on_message(client, userdata, msg):
    global loop
    payload = msg.payload.decode()
    print(f"Ontvangen: {payload}")

    if msg.topic == "train/speed/set":
        try:
            speed = int(float(payload))
            asyncio.run_coroutine_threadsafe(send_speed(speed), loop)
        except ValueError:
            pass
    elif msg.topic == "train/command":
        if payload == "stop":
            asyncio.run_coroutine_threadsafe(send_speed(0), loop)
        elif payload == "forward":
            asyncio.run_coroutine_threadsafe(send_speed(50), loop)
        elif payload == "backward":
            asyncio.run_coroutine_threadsafe(send_speed(-50), loop)
        elif payload == "connect":
            asyncio.run_coroutine_threadsafe(connect_train(), loop)

async def connect_train():
    global client_ble, connected
    if connected:
        return True
    print("Verbinden met trein...")
    try:
        if client_ble:
            try:
                await client_ble.disconnect()
            except:
                pass
        client_ble = BleakClient(TRAIN_MAC, disconnected_callback=lambda c: on_disconnect(c))
        await asyncio.wait_for(client_ble.connect(), timeout=10)
        connected = True
        print("Trein verbonden!")
        mqtt_client.publish("train/status", "online", retain=True)
        return True
    except Exception as e:
        print(f"Verbinding mislukt: {e}")
        connected = False
        return False

async def main():
    global loop, mqtt_client
    loop = asyncio.get_event_loop()

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_message = on_message
    mqtt_client.connect("localhost", 1883)
    mqtt_client.subscribe("train/#")
    mqtt_client.loop_start()

    print("Trein service gestart...")
    mqtt_client.publish("train/status", "offline", retain=True)

    try:
        while True:
            if not connected:
                await connect_train()
            if connected:
                mqtt_client.publish("train/status", "online", retain=True)
            else:
                mqtt_client.publish("train/status", "offline", retain=True)
            mqtt_client.publish("train/speed", str(current_speed))
            await asyncio.sleep(3)
    except KeyboardInterrupt:
        pass
    finally:
        if connected and client_ble:
            await send_speed(0)
            await client_ble.disconnect()
        mqtt_client.publish("train/status", "offline", retain=True)

asyncio.run(main())
