import board
import adafruit_vl53l4cd
import time
import csv
import os
import subprocess
from rplidar import RPLidar
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation

PORT_NAME = '/dev/ttyUSB0'
DMAX = 50
IMIN = 0
IMAX = 100

i2c = board.I2C()
vl53 = adafruit_vl53l4cd.VL53L4CD(i2c)
calibration_val = 1.5
timeout = 0.5  # Timeout in seconds
interval = 5  # Interval in seconds
vl53.start_ranging()


def capture_image(output_path):
    try:
        # Execute the libcamera-still command and capture the output
        cmd = f"libcamera-still --output {output_path} --timeout 5000 --tuning-file /usr/share/libcamera/ipa/rpi/pisp/imx519.json"
        subprocess.run(cmd, shell=True, check=True)
        print(f"Image captured and saved as {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error: libcamera-still command failed with exit code {e.returncode}")
        print(f"Output: {e.output.decode('utf-8')}")
    except Exception as e:
        print(f"Error: {str(e)}")


def update_line(num, iterator, sc):
    scan = next(iterator)
    xs = []
    ys = []
    zs = []
    intens = []
    for meas in scan:
        theta = np.radians(meas[1])
        phi = np.radians(meas[2])
        r = meas[0]
        x = r * np.sin(phi) * np.cos(theta)
        y = r * np.sin(phi) * np.sin(theta)
        z = r * np.cos(phi)
        xs.append(x)
        ys.append(y)
        zs.append(z)
        intens.append(meas[0])
    sc._offsets3d = (xs, ys, zs)
    sc.set_array(np.array(intens))
    return sc,


def run_lidar_visualization():
    lidar = RPLidar(PORT_NAME)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    sc = ax.scatter([0, 0], [0, 0], [0, 0], s=5, c=[IMIN, IMAX], cmap=plt.cm.Greys_r)
    ax.set_xlim([-DMAX, DMAX])
    ax.set_ylim([-DMAX, DMAX])
    ax.set_zlim([0, DMAX])
    ax.grid(True)
    iterator = lidar.iter_scans()
    ani = animation.FuncAnimation(fig, update_line, fargs=(iterator, sc), interval=50)
    plt.show()
    lidar.stop()
    lidar.disconnect()

# Your existing code...

# Open the CSV file in append mode
with open("sensor_data.csv", "a", newline='') as csvfile:
    fieldnames = ["Timestamp", "Height (cm)", "Image Path"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    # Write the headers if the file is empty
    if csvfile.tell() == 0:
        writer.writeheader()

    try:
        while True:
            start_time = time.time()
            # Get the current Unix timestamp
            timestamp = int(time.time())
            # Construct the output filename with the timestamp
            output_filename = f"image_{timestamp}.jpg"
            output_path = os.path.join(os.getcwd(), output_filename)

            # Capture the image
            capture_image(output_path)

            # Wait for sensor data or timeout
            timeout_start = time.time()
            while not vl53.data_ready:
                if time.time() - timeout_start > timeout:
                    print("Timeout waiting for sensor data.")
                    break
            if vl53.data_ready:
                vl53.clear_interrupt()
                distance = vl53.distance - calibration_val

                # Write the data to the CSV file
                writer.writerow({"Timestamp": timestamp, "Height (cm)": distance, "Image Path": output_path})
                print(f"Distance: {distance} cm, Timestamp: {timestamp}, Image Path: {output_path}")

                # Run the LiDAR visualization
                run_lidar_visualization()

            # Wait for the remaining time until the next interval
            elapsed_time = time.time() - start_time
            remaining_time = interval - elapsed_time
            if remaining_time > 0:
                time.sleep(remaining_time)

    except KeyboardInterrupt:
        print("Program interrupted. Data saved to sensor_data.csv.")