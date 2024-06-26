import pandas as pd
import datetime
import pytz

# Read the data file (assuming it's a CSV file)
file_path = '/mnt/data/your_file.csv'  
data = pd.read_csv(file_path)

# Convert the time column from seconds/256 to standard seconds
data['time [s/256]'] = data['time [s/256]'] * 256

# Convert the timestamps to human-readable date and time (New York time)
new_york_tz = pytz.timezone('America/New_York')
data['datetime'] = data['time [s/256]'].apply(lambda x: datetime.datetime.fromtimestamp(x, tz=datetime.timezone.utc).astimezone(new_york_tz).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])

# Save the converted data to a new CSV file
output_file_path = '/mnt/data/converted_file.csv'
data.to_csv(output_file_path, index=False)

print("Conversion complete. The new file is saved as converted_file.csv.")
