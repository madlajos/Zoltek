import porthandler

# Constant tuples for voltages and currents
VOLTAGES = (30, 39, 24, 24, 41, 39)  # Example voltages in volts
CURRENTS = (0.06, 0.50, 0.80, 0.80, 0.50, 0.35)  # Example currents in amps


# This method handles channel control via PSU and lampcontroller commands.
# For safety reasons, it turns all channels off, then sets new PSU values, 
# makes sure they are set correctly, and then turns on the relays.
# It requires psu and lampcontroller objects of porthandler class to be initialised.
def turn_on_channel(channel, on_time_ms, voltage, current):
    """Send command to the PSU."""
    if porthandler.psu is not None:
        # Turn off all channels on the lamp controller
        porthandler.write(porthandler.lampcontroller, "1,0")

        # Send command to set voltage and current
        voltage_command = f"VOLTage {voltage}\n"
        current_command = f"CURRent {current}\n"
        porthandler.write(porthandler.psu, voltage_command)
        porthandler.write(porthandler.psu, current_command)

        # Request set voltage and current from PSU
        porthandler.write(porthandler.psu, "VOLTage?\n")
        set_voltage_response = porthandler.psu.readline().decode().strip()
        porthandler.write(porthandler.psu, "CURRent?\n")
        set_current_response = porthandler.psu.readline().decode().strip()

        # Convert set voltage and current responses to integers
        set_voltage = int(float(set_voltage_response))
        set_current = int(float(set_current_response))

        # Convert predefined voltage and current values to integers
        voltage = int(VOLTAGES[channel - 1])
        current = int(CURRENTS[channel - 1])

        # Check if the responses match the predefined values
        if set_voltage == voltage and set_current == current:
            # If the values match, send command to Lampcontroller
            porthandler.write(porthandler.lampcontroller, (channel, on_time_ms))
        else:
            print("Error: PSU set values do not match")
    else:
        print("Error: PSU is not connected")