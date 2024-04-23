import tkinter as tk
import porthandler  # Import the peripheral connection functions from porthandler.py

# Constant tuples for voltages and currents
VOLTAGES = (30, 39, 24, 24, 41, 39)  # Example voltages in volts
CURRENTS = (0.06, 0.50, 0.80, 0.80, 0.50, 0.35)  # Example currents in amps

def create_window():
    # Create the main window
    window = tk.Tk()
    
    # Set the window title
    window.title("Peripheral Connection")

    # Set window size to 16:9 aspect ratio
    window.geometry("960x540")  # 16 * 60 = 960, 9 * 60 = 540

    # Function to update status indicators
    def update_status_indicator(canvas, connected):
        canvas.delete("status_indicator")
        color = "green" if connected else "red"
        canvas.create_oval(5, 5, 15, 15, fill=color, tags="status_indicator")

    # Function to attempt connection to peripherals
    def connect_to_peripheral(connect_function, canvas, button, device_name):
        device = connect_function()
        if device_name.lower() == "lampcontroller" and device is not None:
            porthandler.lampcontroller = device  # Store lampcontroller object
        if device_name.lower() == "psu" and device is not None:
            porthandler.psu = device  # Store PSU object
        if device is not None:
            update_status_indicator(canvas, True)
            button.config(text=f"Disconnect from {device_name}", command=lambda: disconnect_from_peripheral(device, canvas, button, device_name))
        else:
            update_status_indicator(canvas, False)

    # Function to disconnect from the peripheral
    def disconnect_from_peripheral(device, canvas, button, device_name):
        if device_name.lower() == "lampcontroller":
            porthandler.lampcontroller = None  # Clear lampcontroller object
        device.close()
        update_status_indicator(canvas, False)
        button.config(text=f"Connect to {device_name}", command=lambda: connect_to_peripheral(getattr(porthandler, f"connect_to_{device_name.lower().replace(' ', '_')}"), canvas, button, device_name))

    # Function to send command to Lampcontroller
    def send_command_lampcontroller(channel):
        if porthandler.lampcontroller:
            command = (channel, 3000)
            porthandler.write(porthandler.lampcontroller, command)
        else:
            print("Lampcontroller is not connected.")

    # Function to send command to PSU
    def send_command_psu(channel, voltage, current):
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


    # Function to create buttons for channel numbers
    def create_channel_buttons(frame):
        for i in range(1, 7):
            channel_button = tk.Button(frame, text=str(i), command=lambda ch=i: send_command_psu(ch, VOLTAGES[ch-1], CURRENTS[ch-1]))
            channel_button.pack(side="left", padx=5)

    # Create a frame for the buttons and status indicators
    button_frame = tk.Frame(window)
    button_frame.pack(side="top", fill="x", padx=10, pady=10)

    # Create Owon PSU status indicator and connect button
    psu_canvas = tk.Canvas(button_frame, width=20, height=20)
    psu_canvas.pack(side="left")
    update_status_indicator(psu_canvas, False)  # Initialize as red
    psu_button = tk.Button(button_frame, text="Connect to PSU",
                             command=lambda: connect_to_peripheral(porthandler.connect_to_psu, psu_canvas, psu_button, "PSU"))
    psu_button.pack(side="left")

    # Create Lampcontroller status indicator and connect button
    lamp_canvas = tk.Canvas(button_frame, width=20, height=20)
    lamp_canvas.pack(side="left")
    update_status_indicator(lamp_canvas, False)  # Initialize as red
    lamp_button = tk.Button(button_frame, text="Connect to Lampcontroller",
                             command=lambda: connect_to_peripheral(porthandler.connect_to_lampcontroller, lamp_canvas, lamp_button, "Lampcontroller"))
    lamp_button.pack(side="left")

    # Create 3D Printer status indicator and connect button
    printer_canvas = tk.Canvas(button_frame, width=20, height=20)
    printer_canvas.pack(side="left")
    update_status_indicator(printer_canvas, False)  # Initialize as red
    printer_button = tk.Button(button_frame, text="Connect to 3D Printer",
                                command=lambda: connect_to_peripheral(porthandler.connect_to_printer, printer_canvas, printer_button, "3D Printer"))
    printer_button.pack(side="left")

    # Create a frame for channel buttons
    channel_frame = tk.Frame(window)
    channel_frame.pack(side="top", padx=10, pady=10)
    create_channel_buttons(channel_frame)

    # Run the Tkinter event loop
    window.mainloop()

# Call the function to create the window
create_window()