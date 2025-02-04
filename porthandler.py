import serial
import serial.tools.list_ports
import logging
import time

# Global serial device variables
turntable = None
barcode_scanner = None

def connect_to_serial_device(device_name, identification_command, expected_response, vid, pid):
    """
    Attempt to connect to a serial device by scanning for a matching VID/PID.
    Optionally, send an identification command and compare the response.
    Returns:
        serial.Serial instance if successful, or None.
    """
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        logging.error(f"No COM ports found while looking for {device_name}.")
        return None

    # Filter ports by matching VID/PID.
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

            if identification_command:
                # Send the identification command.
                serial_port.write((identification_command + '\n').encode())
                response = serial_port.readline().decode(errors='ignore').strip()
                logging.info(f"Received response from {port_info.device}: '{response}'")

                if response != expected_response:
                    logging.warning(f"Unexpected response '{response}' on {port_info.device}")
                    serial_port.close()
                    continue  # Try next candidate
            # If no identification command is required, we assume the connection is valid.
            logging.info(f"Connected to {device_name} on port {port_info.device}")
            return serial_port

        except Exception as e:
            logging.exception(
                f"Exception while trying to connect to {device_name} on {port_info.device}: {e}"
            )
            if serial_port and serial_port.is_open:
                serial_port.close()

    logging.error(f"Failed to connect to {device_name}. No matching ports responded correctly.")
    return None


def connect_to_turntable():
    """
    Connects to the turntable using its known identification command and VID/PID.
    """
    global turntable
    if turntable and turntable.is_open:
        logging.info("Turntable is already connected.")
        return turntable

    identification_command = "IDN?"
    expected_response = "TTBL"
    # For the turntable, VID/PID are hard-coded.
    turntable = connect_to_serial_device(
        device_name="Turntable",
        identification_command=identification_command,
        expected_response=expected_response,
        vid=0x2E8A,  # Example VID for turntable
        pid=0x0003   # Example PID for turntable
    )
    if turntable is None:
        raise Exception("Turntable device not found or did not respond correctly.")
    return turntable


def connect_to_barcode_scanner():
    """
    Connects to the barcode scanner (QD2100) using its VID/PID.
    No identification handshake is performed, so pass empty strings.
    """
    global barcode_scanner
    if barcode_scanner and barcode_scanner.is_open:
        logging.info("Barcode scanner is already connected.")
        return barcode_scanner

    # For the barcode scanner, no identification command is needed.
    identification_command = ""
    expected_response = ""
    barcode_scanner = connect_to_serial_device(
        device_name="BarcodeScanner",
        identification_command=identification_command,
        expected_response=expected_response,
        vid=0x05F9,  # Barcode scanner VID (from USB\VID_05F9...)
        pid=0x4204   # Barcode scanner PID (from PID_4204...)
    )
    if barcode_scanner is None:
        raise Exception("Barcode scanner device not found or did not respond correctly.")
    return barcode_scanner


def disconnect_serial_device(device_name):
    """
    Disconnect the specified device ('turntable' or 'barcode').
    """
    global turntable, barcode_scanner
    logging.info(f"Disconnecting {device_name}")
    if device_name.lower() == 'turntable' and turntable is not None:
        try:
            if turntable.is_open:
                turntable.close()
            turntable = None
            logging.info("Turntable disconnected successfully.")
        except Exception as e:
            logging.error(f"Error while disconnecting turntable: {e}")
            raise Exception(f"Failed to disconnect {device_name}: {e}")
    elif device_name.lower() in ['barcode', 'barcodescanner']:
        if barcode_scanner is not None:
            try:
                if barcode_scanner.is_open:
                    barcode_scanner.close()
                barcode_scanner = None
                logging.info("Barcode scanner disconnected successfully.")
            except Exception as e:
                logging.error(f"Error while disconnecting barcode scanner: {e}")
                raise Exception(f"Failed to disconnect {device_name}: {e}")
        else:
            logging.error(f"Barcode scanner not connected.")
            raise Exception(f"Barcode scanner not connected.")
    else:
        logging.error(f"Invalid device name or device not connected: {device_name}")
        raise Exception(f"Invalid device name or device not connected: {device_name}")


def is_turntable_connected():
    """
    Checks if the turntable is still connected and responsive.
    """
    global turntable
    if turntable is None or not turntable.is_open:
        logging.warning("Turntable connection is closed.")
        return False

    try:
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


def is_barcode_scanner_connected():
    """
    Checks if the barcode scanner is still connected.
    For the scanner, since there is no identification handshake,
    we simply verify that the port is open.
    """
    global barcode_scanner
    if barcode_scanner is None or not barcode_scanner.is_open:
        logging.warning("Barcode scanner connection is closed.")
        return False

    try:
        # Optionally, you could try reading a small chunk or sending a NOP command.
        # Here, we simply check the port status.
        return True
    except Exception as e:
        logging.error(f"Barcode scanner error: {e}")
        barcode_scanner.close()
        barcode_scanner = None
        return False




def write_turntable(command, timeout=10):
    """
    Sends a command to the turntable and waits for a clear 'DONE' confirmation.
    """
    global turntable
    if turntable is None or not turntable.is_open:
        raise Exception("Turntable is not connected or available.")

    try:
        if isinstance(command, tuple):
            formatted_command = "{},{}\n".format(*command)
        elif isinstance(command, str):
            formatted_command = f"{command}\n"
        else:
            raise ValueError("Invalid command format. Expected a string or tuple.")

        # Flush buffer before sending a command
        turntable.reset_input_buffer()

        # Send the command
        turntable.write(formatted_command.encode())
        turntable.flush()
        logging.info(f"Command sent to turntable: {formatted_command.strip()}")

        # Read responses until we receive "DONE"
        start_time = time.time()
        received_data = ""

        while time.time() - start_time < timeout:
            if turntable.in_waiting > 0:
                chunk = turntable.read(turntable.in_waiting).decode(errors='ignore')
                received_data += chunk
                logging.info(f"Received from turntable: {chunk.strip()}")

                # If "DONE" is anywhere in the received data, return success
                if "DONE" in received_data:
                    logging.info("Turntable movement completed successfully.")
                    return True

        # Timeout if "DONE" was never received
        logging.warning("Timeout waiting for 'DONE' signal from turntable.")
        return False

    except Exception as e:
        logging.error(f"Error writing to turntable: {str(e)}")
        raise


def write_barcode_scanner(data):
    """
    Sends data to the barcode scanner if needed.
    Typically, barcode scanners stream data automatically when a barcode is scanned.
    This function is provided if you later need to send configuration commands.
    """
    global barcode_scanner
    if barcode_scanner is None or not barcode_scanner.is_open:
        raise Exception("Barcode scanner is not connected or available.")

    try:
        if isinstance(data, str):
            formatted_data = f"{data}\n"
        else:
            formatted_data = str(data) + "\n"
        barcode_scanner.write(formatted_data.encode())
        barcode_scanner.flush()
        logging.info(f"Data sent to barcode scanner: {formatted_data.strip()}")
    except Exception as e:
        logging.error(f"Error writing to barcode scanner: {str(e)}")
        raise
