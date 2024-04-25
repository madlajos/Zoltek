import serial
import serial.tools.list_ports

psu = None
lampcontroller = None
printer = None

def connect_to_device(device_name, identification_command, expected_response):
    for port in serial.tools.list_ports.comports():
        try:
            serial_port = serial.Serial(port.device, baudrate=115200, timeout=1)
            serial_port.write(identification_command.encode() + b'\n')
            response = serial_port.readline().decode().strip()
            if response.startswith(expected_response):
                return serial_port
            else:
                serial_port.close()  # Close the port if the response doesn't match
        except Exception as e:
            continue
    return None

def connect_to_psu():
    identification_command = "*IDN?"
    expected_response = "OWON,"
    
    return connect_to_device("PSU", identification_command, expected_response)

def connect_to_lampcontroller():
    identification_command = "IDN?"
    expected_response = "RPZERO"
    
    return connect_to_device("Lampcontroller", identification_command, expected_response)

def connect_to_printer():
    identification_command = "M115"
    expected_response = "FIRMWARE_NAME:Marlin"
    
    return connect_to_device("printer", identification_command, expected_response)

def write(device, data):
    if isinstance(data, tuple):
        command = "{},{}".format(*data)
    else:
        command = data + "\n"

    if isinstance(device, serial.Serial):
        device.write(command.encode())
    else:
        print("Invalid device type")