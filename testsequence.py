import serial
import time
import porthandler

"""
# Define serial ports for the power supply and Arduino
power_supply_port = "COM19"  # Power supply COM port
power_supply_baudrate = 115200
arduino_port = "COM16"  # Arduino COM port
arduino_baudrate = 115200

# Open serial connections
power_supply = serial.Serial(power_supply_port, baudrate=power_supply_baudrate, bytesize=8, stopbits=1, parity='N', timeout=1)
arduino = serial.Serial(arduino_port, baudrate=arduino_baudrate, timeout=1)

# Function to send SCPI commands to the power supply
def send_command_power_supply(command):
    power_supply.write((command + "\r\n").encode())
    return power_supply.readline().decode().strip()
"""

try:
    #send_command_power_supply("OUTPut OFF")
    
    while True:
        lampcontroller = porthandler.connect_to_lampcontroller()
        if lampcontroller:
            print("Arduino port detected:", lampcontroller.name)
        else:
            print("Arduino port not found. Retrying in 1 second...")
            time.sleep(1)

        power_supply = porthandler.connect_to_PSU()
        if power_supply:
            print("PSU port detected:", power_supply.name)
        else:
            print("PSU port not found. Retrying in 1 second...")
            time.sleep(1)

        porthandler.write(lampcontroller, (1, 1000))

    """while(1):

        send_command_power_supply("VOLTage 30")
        send_command_power_supply("CURRent 0.06")
        if float(send_command_power_supply("VOLTage?")) == 30 and float(send_command_power_supply("CURRent?")) == 0.06:
            send_command_arduino(1, 1000)
            time.sleep(1)

        send_command_power_supply("VOLTage 39")
        send_command_power_supply("CURRent 0.50")
        if float(send_command_power_supply("VOLTage?")) == 39 and float(send_command_power_supply("CURRent?")) == 0.50:
            send_command_arduino(2, 1000)
            time.sleep(1)  

        send_command_power_supply("VOLTage 24")
        send_command_power_supply("CURRent 0.80")
        if float(send_command_power_supply("VOLTage?")) == 24 and float(send_command_power_supply("CURRent?")) == 0.80:
            send_command_arduino(3, 1000)
            time.sleep(1)
        
        send_command_power_supply("VOLTage 24")
        send_command_power_supply("CURRent 0.80")
        if float(send_command_power_supply("VOLTage?")) == 24 and float(send_command_power_supply("CURRent?")) == 0.80:
            send_command_arduino(4, 1000)
            time.sleep(1)

        send_command_power_supply("VOLTage 41")
        send_command_power_supply("CURRent 0.50")
        if float(send_command_power_supply("VOLTage?")) == 41 and float(send_command_power_supply("CURRent?")) == 0.50:
            send_command_arduino(5, 1000)
            time.sleep(1)

        """

except Exception as e:
    print("An error occurred:", e)


finally:
    # Close serial connections
    #power_supply.close()
    #arduino.close()
    print("iu")