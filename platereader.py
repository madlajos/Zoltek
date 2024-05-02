import json

file_path = 'platelist.json'
x0 = 67
y0 = 216

class TabletPlate:
    def __init__(self, name, diameter, height, col_count, row_count, column_distance, row_distance):
        self.name = name
        self.diameter = diameter
        self.height = height
        self.col_count = col_count
        self.row_count = row_count
        self.column_distance = column_distance
        self.row_distance = row_distance

def read_tablet_plates():
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        tablet_plates = []
        for plate_data in data:
            plate = TabletPlate(plate_data['Name'], plate_data['TabletDiameter'], 
                                plate_data['TabletHeight'], plate_data['ColCount'], 
                                plate_data['RowCount'], plate_data['ColumnDistance'], 
                                plate_data['RowDistance'])
            tablet_plates.append(plate)
        
        return tablet_plates
    
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON data from file '{file_path}'.")
        return None

def add_tablet_plate(new_plate):
    try:
        # Read existing tablet plates from the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)

        # Check if a plate with the same name already exists
        for plate_data in data:
            if plate_data['Name'] == new_plate.name:
                print(f"Error: A tablet plate with the name '{new_plate.name}' already exists.")
                return

        # Append new plate data to the existing data
        data.append({
            'Name': new_plate.name,
            'TabletDiameter': new_plate.diameter,
            'TabletHeight': new_plate.height,
            'ColCount': new_plate.col_count,
            'RowCount': new_plate.row_count,
            'ColumnDistance': new_plate.column_distance,
            'RowDistance': new_plate.row_distance
        })

        # Write the updated data back to the JSON file
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

        print("New tablet plate added successfully.")
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON data from file '{file_path}'.")


# Function to update existing plates. If the name is also modified, the function calls
# the add_tablet_plate function with the plate
def update_plate_data(updated_plate):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        # Find the index of the plate to update
        plate_index = None
        for i, plate_data in enumerate(data):
            if plate_data['Name'] == updated_plate.name:
                plate_index = i
                break
        
        # Update the plate data if found, otherwise add a new plate
        if plate_index is not None:
            data[plate_index] = {
                'Name': updated_plate.name,
                'TabletDiameter': updated_plate.diameter,
                'TabletHeight': updated_plate.height,
                'ColCount': updated_plate.col_count,
                'RowCount': updated_plate.row_count,
                'ColumnDistance': updated_plate.column_distance,
                'RowDistance': updated_plate.row_distance
            }
            print(f"Plate '{updated_plate.name}' data updated successfully.")
        else:
            print(f"Plate '{updated_plate.name}' not found. Adding new plate...")
            add_tablet_plate(updated_plate)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON data from file '{file_path}'.")

# Calculates the path array for the printer
def calc_camera_path(plate):
    # Initialize the list to store coordinates
    coordinates = [] 
    x = x0
    y = y0

    # Calculate the coordinates for each tablet
    for _ in range(plate.row_count - 1):
        x = x0  # Reset x coordinate for each new row
        for _ in range(plate.col_count):
            coordinates.append((x, y))
            x += plate.column_distance
        y -= plate.row_distance
        
    return coordinates