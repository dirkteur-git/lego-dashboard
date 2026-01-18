# LEGO Dashboard

LEGO Powered Up integration for Home Assistant on Raspberry Pi.

## Overview

This project provides a Home Assistant integration for controlling LEGO Powered Up devices via Bluetooth, using MQTT for communication with Home Assistant.

## Requirements

- Raspberry Pi with Home Assistant
- Bluetooth adapter (built-in or USB)
- LEGO Powered Up compatible sets
- MQTT broker (Mosquitto)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

1. Find your LEGO train's MAC address using `bluetoothctl` or similar
2. Update `TRAIN_MAC` in `train_service.py`
3. Ensure MQTT broker is running on localhost:1883

## Usage

```bash
python train_service.py
```

## MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `train/status` | Publish | Connection status (online/offline) |
| `train/speed` | Publish | Current speed value |
| `train/speed/set` | Subscribe | Set speed (-100 to 100) |
| `train/command` | Subscribe | Commands: stop, forward, backward, connect |

## Supported Devices

- LEGO Powered Up Hub
- LEGO Technic Hub
- LEGO Train Motor

## License

MIT
