import board
import adafruit_vl53l4cd
import time
import csv

i2c = board.I2C()
vl53 = adafruit_vl53l4cd.VL53L4CD(i2c)
calibration_val = 1.5
timeout = 0.5  # Timeout in seconds

vl53.start_ranging()

# Open the CSV file in append mode
with open("sensor_data.csv", "a", newline='') as csvfile:
    fieldnames = ["Timestamp", "Height (cm)"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    # Write the headers if the file is empty
    if csvfile.tell() == 0:
        writer.writeheader()

    try:
        while True:
            start_time = time.time()

            # Wait for sensor data or timeout
            timeout_start = time.time()
            while not vl53.data_ready:
                if time.time() - timeout_start > timeout:
                    print("Timeout waiting for sensor data.")
                    break

            if vl53.data_ready:
                vl53.clear_interrupt()
                distance = vl53.distance - calibration_val

                # Get the current timestamp
                timestamp = int(time.time())

                # Write the data to the CSV file
                writer.writerow({"Timestamp": timestamp, "Height (cm)": distance})

                print(f"Distance: {distance} cm, Timestamp: {timestamp}")

            # Wait for the remaining time until the next second
            elapsed_time = time.time() - start_time
            remaining_time = 1.0 - elapsed_time
            if remaining_time > 0:
                time.sleep(remaining_time)
    except KeyboardInterrupt:
        print("Program interrupted. Data saved to sensor_data.csv.")
