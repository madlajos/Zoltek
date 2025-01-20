import porthandler
import time

class Turntable:
    def __init__(self, port):
        self.port = port

def move_absolute(turntable, pos):
    # Set the printer to use absolute coordinates
    porthandler.write(turntable, pos)

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