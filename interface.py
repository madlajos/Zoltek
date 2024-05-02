import customtkinter as ctk
import porthandler
import math
import lampcontrols

# Demo project for multi spectral UV lamp.
# Currently does not work, needs refactoring, as turn_on_channel was moved to lampcontrols.

# Set appearance mode to Dark
ctk.set_appearance_mode("Dark")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("Peripheral Connection")
        self.geometry("1200x540")  # Adjusted width to accommodate all buttons

        # Create peripheral buttons
        self.create_peripheral_button("PSU", porthandler.connect_to_psu)
        self.create_peripheral_button("Lampcontroller", porthandler.connect_to_lampcontroller)
        self.create_peripheral_button("Printer", porthandler.connect_to_printer)

        # Create channel buttons
        channel_frame = ctk.CTkFrame(self)
        channel_frame.pack(side="top", padx=10, pady=10)
        self.create_channel_buttons(channel_frame)

        # Create homing buttons
        homing_frame = ctk.CTkFrame(self)
        homing_frame.pack(side="left", padx=20, pady=10)  # Adjusted padx and pady
        self.create_homing_buttons(homing_frame)

        # Create Z-axis control buttons
        z_axis_frame = ctk.CTkFrame(self)
        z_axis_frame.pack(side="left", padx=20, pady=10)  # Adjusted padx and pady
        self.create_z_axis_buttons(homing_frame)

        # Create circular control panel for printer
        self.printer_control_panel = CircularControlPanel(self, self.send_command_printer)
        self.printer_control_panel.pack(side="left", padx=20, pady=10)  # Adjusted padx and pady

    def create_channel_buttons(self, frame):
        """Create buttons for channel numbers."""
        for i in range(1, 7):
            channel_button = ctk.CTkButton(frame, text=str(i), command=lambda ch=i: lampcontrols.turn_on_channel(ch, lampcontrols.VOLTAGES[ch-1], lampcontrols.CURRENTS[ch-1]))
            channel_button.pack(side="left", padx=2)
            channel_button.configure(width=2, height=1)  # Set width and height to make buttons smaller

    def create_peripheral_button(self, device_name, connect_function):
        """Create a button to connect to a peripheral."""
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(side="top", fill="x", padx=10, pady=10)
        canvas = ctk.CTkCanvas(button_frame, width=20, height=20)
        canvas.pack(side="left")
        self.update_status_indicator(canvas, False)  # Initialize as red
        button = ctk.CTkButton(button_frame, text=f"Connect to {device_name}",
                               command=lambda: self.connect_to_peripheral(connect_function, canvas, button, device_name))
        button.pack(side="left")

    def update_status_indicator(self, canvas, connected):
        """Update the status indicator based on connection status."""
        canvas.delete("status_indicator")
        color = "green" if connected else "red"
        canvas.create_oval(5, 5, 15, 15, fill=color, tags="status_indicator")


    #####################################################
    #                                                   #
    #       TODO: REMOVE FROM INTERFACE CLASS!!         #
    #   These methods connect to and disconnect from    #
    #   serial devices and store them as objects.       #   
    #                                                   #
    #####################################################

    def connect_to_peripheral(self, connect_function, canvas, button, device_name):
        """Connect to a peripheral and update UI accordingly."""
        device = connect_function()
        if device is not None:
            if device_name.lower() == "lampcontroller":
                porthandler.lampcontroller = device  # Store lampcontroller object
            elif device_name.lower() == "psu":
                porthandler.psu = device  # Store PSU object
            elif device_name.lower() == "printer":
                porthandler.printer = device  # Store printer object
            self.update_status_indicator(canvas, True)
            button.configure(text=f"Disconnect from {device_name}",
                            command=lambda: self.disconnect_from_peripheral(device, canvas, button, device_name))
        else:
            self.update_status_indicator(canvas, False)

    def disconnect_from_peripheral(self, device, canvas, button, device_name):
        """Disconnect from a peripheral and update UI accordingly."""
        device.close()
        self.update_status_indicator(canvas, False)
        button.configure(text=f"Connect to {device_name}",
                        command=lambda: self.connect_to_peripheral(getattr(porthandler, f"connect_to_{device_name.lower().replace(' ', '_')}"), canvas, button, device_name))


    def send_command_printer(self, command):
        """Send command to the printer."""
        if porthandler.printer is not None:
            porthandler.write(porthandler.printer, command)
        else:
            print("Error: Printer is not connected.")

    def send_command_lampcontroller(self, channel):
        """Send command to the Lampcontroller."""
        if porthandler.lampcontroller:
            command = (channel, 10000)
            porthandler.write(porthandler.lampcontroller, command)
        else:
            print("Lampcontroller is not connected.")

    def create_z_axis_buttons(self, frame):
        """Create buttons for Z-axis control."""
        z_axis_frame = ctk.CTkFrame(self)
        z_axis_frame.pack(side="left", padx=20)

        # Define button commands and labels for Z-axis movement
        z_axis_commands = [("G0 Z10", "+10"), ("G0 Z1", "+1"), ("G0 Z0.1", "+0.1"),
                           ("G0 Z-0.1", "-0.1"), ("G0 Z-1", "-1"), ("G0 Z-10", "-10")]

        # Create buttons for each Z-axis movement
        for command, label in z_axis_commands:
            button = ctk.CTkButton(frame, text=label, command=lambda cmd=command: self.send_command_printer(cmd))
            button.pack(side="top", pady=5)

    def create_homing_buttons(self, frame):
        """Create buttons for homing axes."""
        homing_commands = [("G28 X", "Home X axis"),
                           ("G28 Y", "Home Y axis"),
                           ("G28 Z", "Home Z axis"),
                           ("G28", "Home all axes")]

        for command, label in homing_commands:
            button = ctk.CTkButton(frame, text=label, command=lambda cmd=command: self.send_command_printer(cmd))
            button.pack(side="top", pady=0)

class CircularControlPanel(ctk.CTkFrame):
    def __init__(self, master, printer_control_command, **kwargs):
        super().__init__(master, **kwargs)

        # Define the radius for each circular layout
        radius_10 = 90
        radius_1 = 60
        radius_01 = 30

        # Define the center coordinates of the circular layout
        center_x = 100
        center_y = 100

        # Create buttons for controlling printer movement by 10
        self.create_printer_control_buttons(printer_control_command, radius_10, center_x, center_y, step=10)

        # Create buttons for controlling printer movement by 1
        self.create_printer_control_buttons(printer_control_command, radius_1, center_x, center_y, step=1)

        # Create buttons for controlling printer movement by 0.1
        self.create_printer_control_buttons(printer_control_command, radius_01, center_x, center_y, step=0.1)

    def create_printer_control_buttons(self, printer_control_command, radius, center_x, center_y, step):
        # Define button commands and labels
        button_commands = [("G91\nG0 X{}".format(step), "X +{}".format(step)),
                           ("G91\nG0 Y-{}".format(step), "Y -{}".format(step)),
                           ("G91\nG0 X-{}".format(step), "X -{}".format(step)),
                           ("G91\nG0 Y{}".format(step), "Y +{}".format(step))]

        # Calculate the angle between each button
        angle_delta = 2 * math.pi / len(button_commands)

        # Create buttons and add them to the circular panel
        for i, (command, label) in enumerate(button_commands):
            angle = i * angle_delta
            x = center_x + radius * math.cos(angle) - 10  # Adjusted for button width
            y = center_y + radius * math.sin(angle) - 10  # Adjusted for button height
            button = ctk.CTkButton(self, text=label, command=lambda cmd=command: printer_control_command(cmd), width = 40, height = 20)
            button.place(x=x, y=y)

if __name__ == "__main__":
    app = App()
    app.mainloop()