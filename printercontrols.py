import porthandler
import time

class Printer:
    def __init__(self, port):
        self.port = port

def home_axes(printer, *axes):
    # If no axes are specified, home all axes
    if not axes:
        axes = ['X', 'Y', 'Z']
    else:
        # Ensure each axis has a space between them
        axes = [axis.upper() for axis in axes]

    axes_str = " ".join(axes)
    command = f"G28{axes_str}"

    try:
        porthandler.write(printer, command)
    except Exception as e:
        print(f"An error occured while sending the Homing command to the printer: {e}")

def disable_steppers(printer, *axes):
    # If no axes are specified, disable all steppers
    if not axes:
        axes = ['X', 'Y', 'Z']
    else:
        # Ensure each axis has a space between them
        axes = [axis.upper() for axis in axes]
    
    axes_str = " ".join(axes)
    command = f"M84{axes_str}"

    try:
        porthandler.write(printer, command)
    except Exception as e:
        print(f"An error occured while sending the Disable Steppers command to the printer: {e}")

def get_printer_position(printer, retries=3, delay=1):
    if printer is not None:
        for attempt in range(retries):
            try:
                # Clear the input buffer
                printer.reset_input_buffer()
                
                # Send the M114 command to get the current position
                porthandler.write(printer, "M114")
                response = ""
                while True:
                    line = printer.readline().decode().strip()
                    if line == "ok":
                        break
                    response += line + "\n"
                
                if response:
                    # Parse the response to extract X, Y, and Z positions
                    position = parse_position(response)
                    return position
                else:
                    print("No response from printer.")
                    if attempt < retries - 1:
                        time.sleep(delay)
            except Exception as e:
                print(f"An error occurred while getting the printer position (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
        print("Failed to get printer position after retries.")
        return None
    else:
        print("Invalid device type or printer is not connected")
    return None

def parse_position(response):
    # Example response: "X:10.00 Y:20.00 Z:30.00 E:0.00 Count X:8100 Y:0 Z:4320"
    position = {}
    lines = response.split('\n')
    
    for line in lines:
        if "X:" in line and "Y:" in line and "Z:" in line:
            for axis in ['X', 'Y', 'Z']:
                start = line.find(axis + ":")
                if start != -1:
                    end = line.find(" ", start)
                    value = line[start+2:end]
                    position[axis.lower()] = float(value)
    
    return position

# Moves the printer to a specified location. If the Z coordinate is not given,
# it remains unchanged.
def move_to_position(printer, x_pos, y_pos, z_pos = None):
    # Set the printer to use absolute coordinates
    porthandler.write(printer, "G90")

    # Construct the move command with the specified coordinates
    move_command = f"G1 X{x_pos} Y{y_pos}"
    
    # If a z-coordinate is provided, include it in the move command
    if z_pos is not None:
        move_command += f" Z{z_pos}"

    try:
        # Send the move command to the printer
        porthandler.write(printer, move_command)
    except Exception as e:
        print(f"Error occurred while sending move to position command: {e}")


# Moves the printer by the specified values.
# Can be called with 1-3 arguements, like move_relative(printer, x=1, y=1)
def move_relative(printer, x=None, y=None, z=None):
    # Set the printer to use relative coordinates
    porthandler.write(printer, "G91")

    # Construct the move command with the specified distances
    move_command = "G1"

    # Add x-axis movement if provided
    if x is not None:
        move_command += f" X{x}"

    # Add y-axis movement if provided
    if y is not None:
        move_command += f" Y{y}"

    # Add z-axis movement if provided
    if z is not None:
        move_command += f" Z{z}"

    try:
        # Send the move command to the printer
        porthandler.write(printer, move_command)
    except Exception as e:
        print(f"Error occurred while sending move command: {e}")