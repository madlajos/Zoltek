import json

file_path = 'platelist.json'
x0 = 62.2
y0 = 210

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
