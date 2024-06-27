import os
import porthandler
import json

# Get the current directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the full path to the settings.json file
settings_path = os.path.join(current_dir, 'Angular', 'src', 'assets', 'settings.json')

# Load settings from settings.json
with open(settings_path) as f:
    settings = json.load(f)

# Constants for PSU
VOLTAGES = [ch['voltage'] for ch in settings['channels']]
CURRENTS = [ch['current'] for ch in settings['channels']]

def get_lamp_state():
    if porthandler.lampcontroller is not None:
        porthandler.write(porthandler.lampcontroller, "LS?")
        state = porthandler.lampcontroller.readline().decode().strip()
        return int(state)  # Returns -1 if no channel is active, otherwise returns the active channel number
    else:
        print("Error: Lampcontroller is not connected")
        return -1

def turn_on_channel(channel, on_time_ms):
    """Send command to the PSU."""
    if porthandler.psu is not None:
        current_state = get_lamp_state()
        if current_state == -1:  # No channels are currently on
            # Set the PSU voltage and current
            voltage_command = f"VOLTage {VOLTAGES[channel - 1]}\n"
            current_command = f"CURRent {CURRENTS[channel - 1]}\n"
            porthandler.write(porthandler.psu, voltage_command)
            porthandler.write(porthandler.psu, current_command)

            # If the values match, send command to Lampcontroller
            porthandler.write(porthandler.lampcontroller, (channel, on_time_ms))
        elif current_state == channel:  # The same channel is on
            # Turn off the channel
            porthandler.write(porthandler.lampcontroller, "1,0")
        else:  # A different channel is on
            # Turn off all channels
            porthandler.write(porthandler.lampcontroller, "1,0")

            # Set the PSU voltage and current
            voltage_command = f"VOLTage {VOLTAGES[channel - 1]}\n"
            current_command = f"CURRent {CURRENTS[channel - 1]}\n"
            porthandler.write(porthandler.psu, voltage_command)
            porthandler.write(porthandler.psu, current_command)

            # If the values match, send command to Lampcontroller
            porthandler.write(porthandler.lampcontroller, (channel, on_time_ms))
    else:
        print("Error: PSU is not connected")

def toggle_psu(state):
    if porthandler.psu is not None:
        command = "OUTPut ON" if state else "OUTPut OFF"
        porthandler.write(porthandler.psu, command)
    else:
        print("Error: PSU is not connected")

def get_psu_state():
    if porthandler.psu is not None:
        porthandler.write(porthandler.psu, "OUTPut?")
        state = porthandler.psu.readline().decode().strip()
        return state == "ON"
    return False
