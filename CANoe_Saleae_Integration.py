import os
from datetime import datetime, timedelta
from py_canoe import CANoe
from saleae import automation
from saleae.automation.capture import RadixType
from time import sleep as wait
import pandas as pd
import serial.tools.list_ports
from keyboard import press

# Function to automatically detect the Arduino port
def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Serielles" in port.description:
            return port.device  # Returns the device name, e.g., 'COM3'
    return None

# Function to map the input voltage value from range 0-32
def map_value(x, in_min, in_max, out_min, out_max):
    # Ensure the input value is within the specified range
    if x < in_min:
        x = in_min
    elif x > in_max:
        x = in_max
    return float((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

# Main function for power supply
if __name__ == "__main__":
    arduino_port = find_arduino_port()
    
    if arduino_port:
        print(f"Arduino detected on port: {arduino_port}")
        
        # Initialize and open the serial connection
        serialInst = serial.Serial()
        serialInst.baudrate = 115200
        serialInst.port = arduino_port
        
        try:
            serialInst.open()
            print(f"Serial port {arduino_port} is now open.")
            
            # Read the input voltage value from the user
            press('enter')
            input_value =  12.5

            # Map the input value to the PWM range
            pwm_value = map_value(input_value, 0, 32, 16.7, 236)
                
            # Convert the PWM value to a string and send it over serial
            command = str(pwm_value)
            serialInst.write(command.encode('utf-8'))
                
            print(f"Sent PWM value: {command}")
            print(f"Voltage value set to: {input_value}")

        except Exception as e:
            print(f"Failed to open serial port {arduino_port}: {e}")
    else:
        print("Arduino not found. Please check the connection.")

wait(2)

# Create CANoe object 
canoe_inst = CANoe()

# Open CANoe configuration. Replace canoe_cfg with your configuration file path.
canoe_inst.open(canoe_cfg=r'C:\\Users\\TESTENGI\\Desktop\\Ani\\CANoe_Saleae_Integration\\py_canoe\\BusSimulation\\JLR_NFC_RBS.cfg')

# Start CANoe measurement
canoe_inst.start_measurement()

# Using the `with` statement will automatically call manager.close() when exiting the scope.
with automation.Manager.connect(port=10430) as manager:
    # Configure the capturing device to record on digital channels 0, 1, 2, 3, and 4
    device_configuration = automation.LogicDeviceConfiguration(
        enabled_digital_channels=[0, 1, 2, 3, 4],
        digital_sample_rate=10_000_000,
        digital_threshold_volts=3.3,
    )

    # Record sepcified seconds of data before stopping the capture
    capture_configuration = automation.CaptureConfiguration(
        capture_mode=automation.TimedCaptureMode(duration_seconds=2.0)
    )

    # Start a capture
    with manager.start_capture(
            device_id='458D38700A8662FE',
            device_configuration=device_configuration,
            capture_configuration=capture_configuration) as capture:
        capture.wait()

        # Add an analyzer to the capture
        spi_analyzer = capture.add_analyzer('SPI', label='SPI', settings={
            'MOSI': 0,
            'MISO': 1,
            'Clock': 4,
            'Enable': 3,
            'Bits per Transfer': '8 Bits per Transfer (Standard)'
        })

        export_config = automation.DataTableExportConfiguration(
            analyzer=spi_analyzer,
            radix=RadixType.HEXADECIMAL  # Use hexadecimal format for exported data
        )

        # Export analyzer data to a CSV file
        log_directory = os.path.join(os.getcwd(), "CANoe_Saleae_logs")
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        analyzer_export_filepath = os.path.join(log_directory, f"SPI_{timestamp}.csv")
        capture.export_data_table(
            filepath=analyzer_export_filepath,
            analyzers=[export_config],
            iso8601_timestamp=True
        )
        
        # Save the capture to a file
        capture_filepath = os.path.join(log_directory, f"SPI_{timestamp}.sal")
        capture.save_capture(filepath=capture_filepath)

wait(2)
resp = canoe_inst.send_diag_request('BV_BVEHNFCEMA', '10 01')
resp = canoe_inst.send_diag_request('BV_BVEHNFCEMA', '22 F1 86')

wait(2)
# Stop CANoe Measurement
canoe_inst.stop_measurement()

def open_latest_file(folder_path):
    try:
        files = [f for f in os.scandir(folder_path) if f.is_file()]
        if not files:
            return None
        latest_file = max(files, key=os.path.getmtime)
        return latest_file.path
    except FileNotFoundError:
        print(f"Error: Folder '{folder_path}' not found.")
        return None

# Folder containing the log files
folder_path = "C:\\Users\\TESTENGI\\Desktop\\Ani\\CANoe_Saleae_Integration\\CANoe_Saleae_logs"
latest_file_path = open_latest_file(folder_path)

# Function to process data from the log file
def process_data(filename):
    data = []
    with open(filename, 'r') as f:
        lines = f.readlines()[6:-1]
        for line in lines:
            tokens = line.strip().split()
            timestamp = float(tokens[0])  # Assuming timestamp is in seconds and needs to be a float
            CAN_Protocol = tokens[1]
            Channel = tokens[2]
            Dir = tokens[3]
            CAN_ID = tokens[4]
            Name = tokens[5]
            DLC = tokens[8]
            Data_Length = int(tokens[9])
            CAN_Data = ' '.join(tokens[10:Data_Length+10])
            row = {
                "Timestamp (s)": timestamp,
                "CAN_Protocol/SPI": CAN_Protocol,
                "Channel": Channel,
                "Dir/Type": Dir,
                "CAN_ID": CAN_ID,
                "Name": Name,
                "DLC": DLC,
                "Data_Length": Data_Length,
                "CAN_Data": CAN_Data
            }
            data.append(row)
    return data

# Process the data from the latest file
data = process_data(latest_file_path)

# Convert data to a DataFrame
df = pd.DataFrame(data)

# Read the 12-hour base time from the first line of the file
with open(latest_file_path, 'r') as f:
    lines = f.readlines()[0]
    time_with_marker = " ".join(lines.split()[4:6])  

# Convert 12-hour time to 24-hour format
time_12hr_format = '%I:%M:%S.%f %p'
time_24hr_format = '%H:%M:%S.%f'
parsed_time = datetime.strptime(time_with_marker, time_12hr_format)
time_24hr_str = parsed_time.strftime(time_24hr_format)

# Convert the base time string to a datetime object
base_time = datetime.strptime(time_24hr_str, "%H:%M:%S.%f")

# Add the 'Absolute Timestamp' column
df['Absolute Timestamp'] = df['Timestamp (s)'].apply(lambda x: (base_time + timedelta(seconds=x)).strftime("%H:%M:%S.%f"))

# Specify the desired order of columns
column_order = ['Absolute Timestamp', 'Timestamp (s)', 'CAN_Protocol/SPI', 'Channel', 'Dir/Type', 'CAN_ID', 'Name', 'DLC', 'Data_Length', 'CAN_Data']

# Reorder the columns in the DataFrame
df = df[column_order]

base_filename = os.path.basename(latest_file_path)
output_filename = os.path.splitext(base_filename)[0] + '.xlsx'
output_file_path = os.path.join("CANoe_Saleae_logs", output_filename)

# Save the modified DataFrame to an Excel file with the same name as the latest log file
df.to_excel(output_file_path, index=False)

# Read the CSV file into a DataFrame
df = pd.read_csv(analyzer_export_filepath)

# Define the new column names
new_column_names = {
    'name': 'CAN_Protocol/SPI',
    'type': 'Dir/Type',
    'start_time': 'Absolute Timestamp',
    'duration': 'Timestamp (s)',
    'mosi': 'MOSI',
    'miso': 'MISO'
}

# Rename the columns
df.rename(columns=new_column_names, inplace=True)

# Convert and format the 'Absolute Timestamp' column
df['Absolute Timestamp'] = pd.to_datetime(df['Absolute Timestamp'])
df['Absolute Timestamp'] = df['Absolute Timestamp'].dt.strftime('%H:%M:%S.%f')
df['Absolute Timestamp'] = pd.to_datetime(df['Absolute Timestamp'], format='%H:%M:%S.%f') + timedelta(hours=2)

# Save the updated DataFrame back to a CSV file
SPI_xlsx_filepath = os.path.join(log_directory, f"SPI_{timestamp}.xlsx")
df.to_excel(SPI_xlsx_filepath, index=False)

# Directory where the log files are stored
log_directory = os.path.join(os.getcwd(), "CANoe_Saleae_logs")

# Read the Excel files into DataFrames
df1 = pd.read_excel(SPI_xlsx_filepath)
df2 = pd.read_excel(output_file_path)

# Add an index column to keep track of the original row order
df1['OriginalIndex'] = range(len(df1))
df2['OriginalIndex'] = range(len(df2))

# Concatenate DataFrames vertically, ensuring the columns are aligned properly
merged_df = pd.concat([df1, df2], ignore_index=True)

# Convert 'Absolute Timestamp' to datetime objects
merged_df['Absolute Timestamp'] = pd.to_datetime(merged_df['Absolute Timestamp'], format="%H:%M:%S.%f", errors='coerce')

# Sort the DataFrame by 'Absolute Timestamp' and 'OriginalIndex'
df_sorted = merged_df.sort_values(by=['Absolute Timestamp', 'OriginalIndex'])

# Convert 'Absolute Timestamp' back to string format
df_sorted['Absolute Timestamp'] = df_sorted['Absolute Timestamp'].dt.strftime("%H:%M:%S.%f")

# Drop the 'OriginalIndex' column
df_sorted = df_sorted.drop(columns=['OriginalIndex'])

# Define the path for the sorted Excel file
sorted_excel_filepath = os.path.join(log_directory, f"Merged_Sorted_{timestamp}.xlsx")

# Save the sorted DataFrame to a new Excel file
df_sorted.to_excel(sorted_excel_filepath, index=False)

expected_messages = [
    {"CAN_ID": "7df", "CAN_Data": "10 01"},
    {"CAN_ID": "73e", "CAN_Data": "50 01"},
    {"CAN_ID": "7df", "CAN_Data": "22 f1 86"},
    {"CAN_ID": "73e", "CAN_Data": "62 f1 86 01"}
]

# Load the Excel file
file_path = output_file_path

df = pd.read_excel(file_path, sheet_name='Sheet1')

# Function to check if expected messages are present
def check_partial_messages(df, expected_messages):
    results = []
    for msg in expected_messages:
        # Check if the expected CAN_Data is a substring of any CAN_Data for the same CAN_ID
        found = df[(df['CAN_ID'] == msg['CAN_ID']) & df['CAN_Data'].str.contains(msg['CAN_Data'])].any().any()
        results.append({
            "CAN_ID": msg['CAN_ID'],
            "Expected_CAN_Data": msg['CAN_Data'],
            "Received": found
        })
    return pd.DataFrame(results)

# Check the messages
results_df = check_partial_messages(df, expected_messages)

# Display the results
print(results_df)

command = "0"
serialInst.write(command.encode('utf-8'))

# Quit / Close CANoe configuration
# canoe_inst.quit()  # Uncomment this if you are using the CANoe instance
