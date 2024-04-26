import porthandler

def home_axes(printer, *axes):
    # If no axes are specified, home all axes
    if not axes:
        axes = ['X', 'Y', 'Z']
    else:
        # Ensure each axis has a space between them
        axes = [axis.upper() for axis in axes]

    axes_str = " ".join(axes)
    command = f"G28 {axes_str}"

    try:
        porthandler.write(printer, command)
    except Exception as e:
        print(f"An error occured while sending the homing command to the printer: {e}")

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
