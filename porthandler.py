import serial.tools.list_ports
import serial

# Function to scan and connect to the Owon Power Supply.
# 'IDN?' command should return the descriptor of the device.
def connect_to_psu():
    for port in serial.tools.list_ports.comports():
        try:
            serial_port = serial.Serial(port.device, baudrate=115200, bytesize=8, stopbits=1,
                                         parity='N', timeout=1)

            serial_port.write(b"*IDN?\n")
            
            response = serial_port.readline().decode().strip()
            if response.startswith("OWON,"):
                return serial_port
            else:
                serial_port.close()

        except serial.SerialException:
            continue

    return None

# Function to scan and connect to the UV Lamp Relay Controller (WaveShare RP2040 Zero).
# 'IDN?' command should return the identification of the device 'RPZERO'.
def connect_to_lampcontroller():
    for port in serial.tools.list_ports.comports():
        try:
            serial_port = serial.Serial(port.device, baudrate=115200, timeout=1)
            # Assuming there's some kind of handshake or identification process here
            # For example, sending a command and waiting for a response
            serial_port.write(b"IDN?\n")
            response = serial_port.readline().decode().strip()
            if response.startswith("RPZERO"):
                return serial_port
        except Exception as e:
            continue
    return None

# Function to scan and connect to the 3D Printer running Marlin FW.
# M115 command should return the basic descriptor of the FW.
def connect_to_printer():
    for port in serial.tools.list_ports.comports():
        try:
            serial_port = serial.Serial(port.device, baudrate=115200, bytesize=8, stopbits=1,
                                         parity='N', timeout=1)

            serial_port.write(b"M115\n")
            response = serial_port.readline().decode().strip()

            if response.startswith("FIRMWARE_NAME:Marlin"):
                return serial_port
            else:
                serial_port.close()

        except serial.SerialException:
            continue

    return None


def write(device, data):
    if isinstance(data, tuple):
        # Format command for lampcontroller
        command = "{},{}".format(*data)
    elif device == "psu":
        # Format command for PSU
        command = data + "\n"  # Add a newline character at the end for PSU commands
    else:
        # Default behavior
        command = data

    # Write command to the serial port
    if isinstance(device, serial.Serial):
        device.write(command.encode())
    else:
        print("Invalid device type")