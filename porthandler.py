import serial
import serial.tools.list_ports
import logging

turntable = None

def connect_to_serial_device(device_name, identification_command, expected_response):
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

def disconnect_serial_device(device_name):
    global turntable
    logging.info(f"Disconnecting {device_name}")
    if device_name == 'turntable' and turntable is not None:
        turntable.close()
        turntable = None
        logging.info("Turntable disconnected successfully.")

    else:
        logging.error(f"Invalid device name or device not connected: {device_name}")
        raise Exception(f"Invalid device name or device not connected: {device_name}")

def connect_to_turntable():
    global turntable
    identification_command = "IDN?"
    expected_response = "TTBL"
    turntable = connect_to_serial_device("Turntable", identification_command, expected_response)
    return turntable

def get_turntable():
    global turntable
    if turntable is None:
        turntable = connect_to_turntable()
        if not turntable:
            raise Exception("Turntable device not found")
    return turntable

def write_turntable(command):
    """
    Sends a command to the turntable.

    Args:
        command (str or tuple): The command to send, either as a string or tuple.

    Raises:
        ValueError: If the command format is invalid.
        Exception: If the device is not connected.
    """
    global turntable

    if turntable is None or not turntable.is_open:
        raise Exception("Turntable is not connected or available.")

    try:
        # Format command based on type
        if isinstance(command, tuple):
            formatted_command = "{},{}\n".format(*command)
        elif isinstance(command, str):
            formatted_command = f"{command}\n"
        else:
            raise ValueError("Invalid command format. Expected a string or tuple.")

        # Send command to serial device
        turntable.write(formatted_command.encode())
        turntable.flush()

        logging.info(f"Command sent to turntable: {formatted_command.strip()}")

    except Exception as e:
        logging.error(f"Error writing to turntable: {str(e)}")
        raise  # Rethrow the exception for higher-level handling