import serial
import serial.tools.list_ports
import logging

psu = None
lampcontroller = None
printer = None

def connect_to_device(device_name, identification_command, expected_response):
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        logging.error(f"No COM ports found for {device_name}.")
        return None

    for port in ports:
        try:
            serial_port = serial.Serial(port.device, baudrate=115200, timeout=1)
            serial_port.write(identification_command.encode() + b'\n')
            response = serial_port.readline().decode().strip()
            if response.startswith(expected_response):
                logging.info(f"Connected to {device_name} on port {port.device}")
                return serial_port
            else:
                logging.info(f"{device_name} did not respond correctly on port {port.device}")
                serial_port.close()  # Close the port if the response doesn't match
        except Exception as e:
            logging.exception(f"Exception occurred while trying to connect to {device_name} on port {port.device}")
            continue

    logging.error(f"Failed to connect to {device_name}. No matching ports found.")
    return None

def disconnect_device(device_name):
    global psu, lampcontroller, printer
    logging.info(f"Disconnecting {device_name}")
    if device_name == 'psu' and psu is not None:
        psu.close()
        psu = None
        logging.info("PSU disconnected successfully.")
    elif device_name == 'lampcontroller' and lampcontroller is not None:
        lampcontroller.close()
        lampcontroller = None
        logging.info("Lampcontroller disconnected successfully.")
    elif device_name == 'printer' and printer is not None:
        printer.close()
        printer = None
        logging.info("Printer disconnected successfully.")
    else:
        logging.error(f"Invalid device name or device not connected: {device_name}")
        raise Exception(f"Invalid device name or device not connected: {device_name}")

def connect_to_psu():
    global psu
    identification_command = "*IDN?"
    expected_response = "OWON,"
    psu = connect_to_device("PSU", identification_command, expected_response)
    return psu

def connect_to_lampcontroller():
    global lampcontroller
    identification_command = "IDN?"
    expected_response = "RPZERO"
    lampcontroller = connect_to_device("Lampcontroller", identification_command, expected_response)
    return lampcontroller

def connect_to_printer():
    global printer
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
    return psu

def get_lampcontroller():
    global lampcontroller
    if lampcontroller is None:
        lampcontroller = connect_to_lampcontroller()
        if not lampcontroller:
            raise Exception("Lampcontroller not found")
    return lampcontroller

def get_printer():
    global printer
    if not printer:
        logging.error("Printer not connected.")
        return None
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
