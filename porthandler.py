import serial
import serial.tools.list_ports
import logging

turntable = None

def connect_to_serial_device(device_name, identification_command, expected_response, 
                             vid=0x2341, pid=0x8036):
    """
    Attempt to connect to a serial device by scanning for a matching VID/PID.
    Then verify the device by sending an identification command and comparing the response.
    """
    global turntable
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        logging.error(f"No COM ports found at all while looking for {device_name}.")
        return None
    
    # Filter ports by known vid/pid
    matching_ports = [
        port for port in ports
        if (port.vid == vid and port.pid == pid)
    ]
    if not matching_ports:
        logging.warning(f"No ports found with VID=0x{vid:04x} PID=0x{pid:04x} for {device_name}.")
        return None

    logging.info(f"Found {len(matching_ports)} candidate port(s) for {device_name} by VID/PID.")
    
    for port_info in matching_ports:
        serial_port = None
        try:
            logging.info(f"Trying {port_info.device} for {device_name}.")
            serial_port = serial.Serial(port_info.device, baudrate=115200, timeout=1)

            # Send the ID command
            serial_port.write((identification_command + '\n').encode())
            response = serial_port.readline().decode(errors='ignore').strip()
            logging.info(f"Received response from {port_info.device}: '{response}'")

            if response == expected_response:
                logging.info(f"Connected to {device_name} on port {port_info.device}")
                turntable = serial_port  # store globally
                return serial_port

            # If response is not what we expect, log and move on
            logging.warning(f"Unexpected response '{response}' on {port_info.device}")
        except Exception as e:
            logging.exception(
                f"Exception occurred while trying to connect to {device_name} on {port_info.device}: {e}"
            )
        finally:
            # If not the correct device, close the port
            if serial_port and serial_port.is_open and turntable != serial_port:
                logging.info(f"Closing {port_info.device}, no successful ID match.")
                serial_port.close()

    logging.error(f"Failed to connect to {device_name}. No matching ports responded correctly.")
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
    turntable = connect_to_serial_device(
        device_name="Turntable", 
        identification_command=identification_command, 
        expected_response=expected_response,
        vid=0x2341,
        pid=0x8036
    )
    if turntable is None:
        raise Exception("Turntable device not found or did not respond correctly.")
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