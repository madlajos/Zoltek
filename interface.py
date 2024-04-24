import tkinter as tk
import porthandler

# Constant tuples for voltages and currents
VOLTAGES = (30, 39, 24, 24, 41, 39)  # Example voltages in volts
CURRENTS = (0.06, 0.50, 0.80, 0.80, 0.50, 0.35)  # Example currents in amps

def update_status_indicator(canvas, connected):
    """Update the status indicator based on connection status."""
    canvas.delete("status_indicator")
    color = "green" if connected else "red"
    canvas.create_oval(5, 5, 15, 15, fill=color, tags="status_indicator")

def connect_to_peripheral(connect_function, canvas, button, device_name):
    """Connect to a peripheral and update UI accordingly."""
    device = connect_function()
    if device is not None:
        if device_name.lower() == "lampcontroller":
            porthandler.lampcontroller = device  # Store lampcontroller object
        elif device_name.lower() == "psu":
            porthandler.psu = device  # Store PSU object
        elif device_name.lower() == "printer":
            porthandler.printer = device  # Store printer object
        update_status_indicator(canvas, True)
        button.config(text=f"Disconnect from {device_name}",
                      command=lambda: disconnect_from_peripheral(device, canvas, button, device_name))
    else:
        update_status_indicator(canvas, False)

def disconnect_from_peripheral(device, canvas, button, device_name):
    """Disconnect from a peripheral and update UI accordingly."""
    device.close()
    update_status_indicator(canvas, False)
    button.config(text=f"Connect to {device_name}",
                  command=lambda: connect_to_peripheral(getattr(porthandler, f"connect_to_{device_name.lower().replace(' ', '_')}"), canvas, button, device_name))

def send_command_psu(channel, voltage, current):
    """Send command to the PSU."""
    if porthandler.psu is not None:
        # Send command to set voltage and current
        voltage_command = f"VOLTage {voltage}\n"
        current_command = f"CURRent {current}\n"
        porthandler.write(porthandler.psu, voltage_command)
        porthandler.write(porthandler.psu, current_command)
        # Request set voltage and current from PSU
        porthandler.write(porthandler.psu, "VOLTage?\n")
        set_voltage_response = porthandler.psu.readline().decode().strip()
        porthandler.write(porthandler.psu, "CURRent?\n")
        set_current_response = porthandler.psu.readline().decode().strip()
        # Convert set voltage and current responses to integers
        set_voltage = int(float(set_voltage_response))
        set_current = int(float(set_current_response))
        # Convert predefined voltage and current values to integers
        voltage = int(VOLTAGES[channel - 1])
        current = int(CURRENTS[channel - 1])
        # Check if the responses match the predefined values
        if set_voltage == voltage and set_current == current:
            # If the values match, send command to Lampcontroller
            send_command_lampcontroller(channel)
        else:
            print("Error: PSU set values do not match")
    else:
        print("Error: PSU is not connected")

def send_command_lampcontroller(channel):
    """Send command to the Lampcontroller."""
    if porthandler.lampcontroller:
        command = (channel, 3000)
        porthandler.write(porthandler.lampcontroller, command)
    else:
        print("Lampcontroller is not connected.")


def create_channel_buttons(frame):
    """Create buttons for channel numbers."""
    for i in range(1, 7):
        channel_button = tk.Button(frame, text=str(i), command=lambda ch=i: send_command_psu(ch, VOLTAGES[ch-1], CURRENTS[ch-1]))
        channel_button.pack(side="left", padx=5)

def create_peripheral_button(window, device_name, connect_function):
    """Create a button to connect to a peripheral."""
    button_frame = tk.Frame(window)
    button_frame.pack(side="top", fill="x", padx=10, pady=10)
    canvas = tk.Canvas(button_frame, width=20, height=20)
    canvas.pack(side="left")
    update_status_indicator(canvas, False)  # Initialize as red
    button = tk.Button(button_frame, text=f"Connect to {device_name}",
                       command=lambda: connect_to_peripheral(connect_function, canvas, button, device_name))
    button.pack(side="left")

def create_window():
    """Create the main window."""
    window = tk.Tk()
    window.title("Peripheral Connection")
    window.geometry("960x540")
    create_peripheral_button(window, "PSU", porthandler.connect_to_psu)
    create_peripheral_button(window, "Lampcontroller", porthandler.connect_to_lampcontroller)
    create_peripheral_button(window, "3D Printer", porthandler.connect_to_printer)
    channel_frame = tk.Frame(window)
    channel_frame.pack(side="top", padx=10, pady=10)
    create_channel_buttons(channel_frame)
    window.mainloop()

# Call the function to create the window
create_window()
