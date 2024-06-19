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
    psu = connect_to_device("PSU", identification_command, expected_response)
    return psu

def connect_to_lampcontroller():
    identification_command = "IDN?"
    expected_response = "RPZERO"
    lampcontroller = connect_to_device("Lampcontroller", identification_command, expected_response)
    return lampcontroller

def connect_to_printer():
    identification_command = "M115"
    expected_response = "FIRMWARE_NAME:Marlin"
    printer = connect_to_device("printer", identification_command, expected_response)
    return printer

def get_psu():
    global psu
    if psu is None:
        psu = connect_to_psu()
        if not psu:
            raise Exception("PSU not found")
    return printer

def get_lampcontroller():
    global lampcontroller
    if lampcontroller is None:
        psu = connect_to_lampcontroller()
        if not printer:
            raise Exception("Lampcontroller not found")
    return printer

def get_printer():
    global printer
    if printer is None:
        printer = connect_to_printer()
        if not printer:
            raise Exception("Printer not found")
    return printer

def write(device, data):
    if isinstance(data, tuple):
        command = "{},{}".format(*data)
    else:
        command = data + "\n"

    if isinstance(device, serial.Serial):
        device.write(command.encode())
    else:
        print("Invalid device type")