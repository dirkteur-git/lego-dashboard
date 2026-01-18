import asyncio
from bleak import BleakClient, BleakScanner
import paho.mqtt.client as mqtt

TRAIN_MAC = "XX:XX:XX:XX:XX:XX"  # Vervang met jouw MAC adres
CHAR_UUID = "00001624-1212-efde-1623-785feabcd123"

client_ble = None
current_speed = 0
current_color = 0
loop = None
connected = False
mqtt_client = None

# LED kleuren (0-10 palette)
LED_COLORS = [0x00, 0x03, 0x05, 0x06, 0x07, 0x09, 0x0A]  # off, blue, cyan, green, yellow, red, purple

# Duplo Train ports
PORT_LED = 0x11    # LED port op Duplo Train Hub (port 17)
PORT_MOTOR = 0x00  # Motor port
PORT_SPEAKER = 0x01  # Speaker port

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

async def set_led_color(color_index):
    global client_ble, connected, current_color
    if not connected or not client_ble:
        print("Niet verbonden")
        return False
    try:
        color = LED_COLORS[color_index % len(LED_COLORS)]
        # Eerst mode instellen voor LED (port 0x11 = 17)
        mode_cmd = bytes([0x0a, 0x00, 0x41, PORT_LED, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00])
        await client_ble.write_gatt_char(CHAR_UUID, mode_cmd)
        await asyncio.sleep(0.05)
        # Dan kleur instellen
        color_cmd = bytes([0x08, 0x00, 0x81, PORT_LED, 0x11, 0x51, 0x00, color])
        await client_ble.write_gatt_char(CHAR_UUID, color_cmd)
        current_color = color_index
        print(f"LED kleur: {color_index} (0x{color:02x})")
        return True
    except Exception as e:
        print(f"Fout LED: {e}")
        return False

async def play_sound(sound=0x09):
    global client_ble, connected
    if not connected or not client_ble:
        print("Niet verbonden")
        return False
    try:
        # Duplo Train heeft speaker op port 0x01
        # Eerst mode instellen voor sound
        mode_cmd = bytes([0x0a, 0x00, 0x41, PORT_SPEAKER, 0x01, 0x01, 0x00, 0x00, 0x00, 0x01])
        await client_ble.write_gatt_char(CHAR_UUID, mode_cmd)
        await asyncio.sleep(0.05)
        # Dan geluid afspelen (0x09 = horn/toeter)
        sound_cmd = bytes([0x08, 0x00, 0x81, PORT_SPEAKER, 0x11, 0x51, 0x01, sound])
        await client_ble.write_gatt_char(CHAR_UUID, sound_cmd)
        print(f"Geluid: {sound}")
        return True
    except Exception as e:
        print(f"Fout geluid: {e}")
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
            delta = int(float(payload))
            # Relatieve snelheid: tel op bij huidige snelheid
            new_speed = max(-100, min(100, current_speed + delta))
            asyncio.run_coroutine_threadsafe(send_speed(new_speed), loop)
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
        elif payload == "color":
            asyncio.run_coroutine_threadsafe(set_led_color(current_color + 1), loop)
        elif payload == "horn":
            asyncio.run_coroutine_threadsafe(play_sound(), loop)

async def connect_train():
    global client_ble, connected
    if connected:
        return True
    print("Zoeken naar trein...")
    try:
        if client_ble:
            try:
                await client_ble.disconnect()
            except:
                pass

        # Scan voor de trein
        device = await BleakScanner.find_device_by_address(TRAIN_MAC, timeout=5.0)
        if not device:
            print("Trein niet gevonden")
            return False

        print(f"Trein gevonden! Verbinden...")
        client_ble = BleakClient(device, disconnected_callback=lambda c: on_disconnect(c))
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
