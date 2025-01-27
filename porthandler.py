import serial
import serial.tools.list_ports
import logging

turntable = None

def connect_to_serial_device(device_name, identification_command, expected_response):
    global turntable
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        logging.error(f"No COM ports found for {device_name}.")
        return None

    for port in ports:
        try:
            logging.info(f"Trying port {port.device} for {device_name}")
            serial_port = serial.Serial(port.device, baudrate=115200, timeout=1)

            serial_port.write(identification_command.encode() + b'\n')
            response = serial_port.readline().decode(errors='ignore').strip()
            logging.info(f"Received response from {port.device}: '{response}'")

            if response == expected_response:
                logging.info(f"Connected to {device_name} on port {port.device}")
                turntable = serial_port  # Store active connection globally
                return serial_port  # Return the connection

            logging.warning(f"Unexpected response '{response}' from {device_name} on {port.device}")

        except Exception as e:
            logging.exception(f"Exception occurred while trying to connect to {device_name} on {port.device}: {e}")

        finally:
            if serial_port and serial_port.is_open and response != expected_response:
                logging.info(f"Closing {port.device}, no successful ID match.")
                serial_port.close()

    logging.error(f"Failed to connect to {device_name}. No matching ports found.")
    return None


def disconnect_serial_device(device_name):
    global turntable
    logging.info(f"Disconnecting {device_name}")
    if device_name == 'turntable' and turntable is not None:
        try:
            if turntable.is_open:
                turntable.close()
            turntable = None
            logging.info("Turntable disconnected successfully.")
        except Exception as e:
            logging.error(f"Error while disconnecting turntable: {e}")
            raise Exception(f"Failed to disconnect {device_name}: {e}")
    else:
        logging.error(f"Invalid device name or device not connected: {device_name}")
        raise Exception(f"Invalid device name or device not connected: {device_name}")

def connect_to_turntable():
    global turntable
    if turntable and turntable.is_open:
        logging.info("Turntable is already connected.")
        return turntable
    
    identification_command = "IDN?"
    expected_response = "TTBL"
    turntable = connect_to_serial_device("Turntable", identification_command, expected_response)
    if turntable is None:
        raise Exception("Turntable device not found")
    return turntable

def get_turntable():
    global turntable
    if turntable is None:
        turntable = connect_to_turntable()
        if not turntable:
            raise Exception("Turntable device not found")
    return turntable

def is_turntable_connected():
    """
    Checks if the turntable is still connected and responsive.

    Returns:
        bool: True if the device is still connected and responsive, False otherwise.
    """
    global turntable

    if turntable is None or not turntable.is_open:
        logging.warning("Turntable connection is closed.")
        return False

    try:
        # Attempt a simple command to verify device responsiveness
        turntable.write(b'IDN?\n')
        response = turntable.readline().decode(errors='ignore').strip()
        logging.debug(f"Turntable response: {response}")

        if response:
            return True

    except (serial.SerialException, serial.SerialTimeoutException) as e:
        logging.error(f"Turntable disconnected or unresponsive: {e}")
        turntable.close()
        turntable = None
        return False

    logging.warning("Turntable did not respond. Marking as disconnected.")
    turntable.close()
    turntable = None
    return False

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