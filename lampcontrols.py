import porthandler
import json

# Load settings from the JSON file
def load_settings():
    with open('D:/source/TabletScanner/Angular/src/assets/settings.json') as f:
        settings = json.load(f)
    return settings

SETTINGS = load_settings()

def get_lamp_state():
    if porthandler.lampcontroller is not None:
        porthandler.write(porthandler.lampcontroller, "GETLAMPSTATE")
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
            voltage = SETTINGS['channels'][channel - 1]['voltage']
            current = SETTINGS['channels'][channel - 1]['current']
            
            voltage_command = f"VOLTage {voltage}\n"
            current_command = f"CURRent {current}\n"
            porthandler.write(porthandler.psu, voltage_command)
            porthandler.write(porthandler.psu, current_command)

            # Request set voltage and current from PSU
            porthandler.write(porthandler.psu, "VOLTage?\n")
            set_voltage_response = porthandler.psu.readline().decode().strip()
            porthandler.write(porthandler.psu, "CURRent?\n")
            set_current_response = porthandler.psu.readline().decode().strip()

            # Convert set voltage and current responses to floats
            set_voltage = float(set_voltage_response)
            set_current = float(set_current_response)

            # Convert predefined voltage and current values to floats
            voltage = float(voltage)
            current = float(current)

            print(f"Set voltage: {set_voltage}, Expected voltage: {voltage}")
            print(f"Set current: {set_current}, Expected current: {current}")

            # Check if the responses match the predefined values
            if abs(set_voltage - voltage) < 0.01 and abs(set_current - current) < 0.01:  # Allowing a small tolerance
                # Turn on the PSU output
                porthandler.write(porthandler.psu, "OUTPut ON")
                
                # If the values match, send command to Lampcontroller
                porthandler.write(porthandler.lampcontroller, (channel, on_time_ms))
            else:
                print("Error: PSU set values do not match")
        elif current_state == channel:  # The same channel is on
            # Turn off the channel
            porthandler.write(porthandler.lampcontroller, "1,0")
        else:  # A different channel is on
            # Turn off all channels
            porthandler.write(porthandler.lampcontroller, "1,0")

            # Set the PSU voltage and current
            voltage = SETTINGS['channels'][channel - 1]['voltage']
            current = SETTINGS['channels'][channel - 1]['current']
            
            voltage_command = f"VOLTage {voltage}\n"
            current_command = f"CURRent {current}\n"
            porthandler.write(porthandler.psu, voltage_command)
            porthandler.write(porthandler.psu, current_command)

            # Request set voltage and current from PSU
            porthandler.write(porthandler.psu, "VOLTage?\n")
            set_voltage_response = porthandler.psu.readline().decode().strip()
            porthandler.write(porthandler.psu, "CURRent?\n")
            set_current_response = porthandler.psu.readline().decode().strip()

            # Convert set voltage and current responses to floats
            set_voltage = float(set_voltage_response)
            set_current = float(set_current_response)

            # Convert predefined voltage and current values to floats
            voltage = float(voltage)
            current = float(current)

            print(f"Set voltage: {set_voltage}, Expected voltage: {voltage}")
            print(f"Set current: {set_current}, Expected current: {current}")

            # Check if the responses match the predefined values
            if abs(set_voltage - voltage) < 0.01 and abs(set_current - current) < 0.01:  # Allowing a small tolerance
                # Turn on the PSU output
                porthandler.write(porthandler.psu, "OUTPut ON")
                
                # If the values match, send command to Lampcontroller
                porthandler.write(porthandler.lampcontroller, (channel, on_time_ms))
            else:
                print("Error: PSU set values do not match")
    else:
        print("Error: PSU is not connected")
