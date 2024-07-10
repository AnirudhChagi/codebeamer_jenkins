import os
import pandas as pd
from saleae import automation
from datetime import datetime
from saleae.automation.capture import RadixType

# Using the `with` statement will automatically call manager.close() when exiting the scope.
with automation.Manager.connect(port=10430) as manager:

    # Configure the capturing device to record on digital channels 0, 1, 2, 3, and 4
    device_configuration = automation.LogicDeviceConfiguration(
        enabled_digital_channels=[0, 1, 2, 3, 4],
        digital_sample_rate=10_000_000,
        digital_threshold_volts=3.3,
        )

    # Record 2 seconds of data before stopping the capture
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
        analyzer_export_filepath = os.path.join(os.getcwd(), "CANoe_Saleae_logs", f"SPI_{datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}.csv")
        capture.export_data_table(
            filepath=analyzer_export_filepath,
            analyzers=[export_config],
            iso8601_timestamp=True
        )
        
        # Finally, save the capture to a file
        capture_filepath = os.path.join(os.getcwd(),"CANoe_Saleae_logs", f"SPI_{datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}.sal")
        capture.save_capture(filepath=capture_filepath)



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

# Save the updated DataFrame back to a CSV file
log_directory = os.path.join(os.getcwd(), "CANoe_Saleae_logs")
timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
new_csv_filepath = os.path.join(log_directory, f"SPI_{timestamp}.xlsx")
df.to_excel(new_csv_filepath, index=False)
