import board
import adafruit_vl53l4cd
import time
import os
import subprocess
import adafruit_bno055
import busio
import numpy as np

# Initialize I2C interface 
i2c = board.I2C()

# Initialize Time-of-Flight Sensor
tof_sensor = adafruit_vl53l4cd.VL53L4CD(i2c)
tof_calibration = 1.5
timeout = 0.5  # Timeout in seconds
interval = 5   # Interval in seconds
tof_sensor.start_ranging()

# Initialize Initial Measurement Sensor
class Mode:
    CONFIG_MODE = 0x00
    ACCONLY_MODE = 0x01
    MAGONLY_MODE = 0x02
    GYRONLY_MODE = 0x03
    ACCMAG_MODE = 0x04
    ACCGYRO_MODE = 0x05
    MAGGYRO_MODE = 0x06
    AMG_MODE = 0x07
    IMUPLUS_MODE = 0x08
    COMPASS_MODE = 0x09
    M4G_MODE = 0x0A
    NDOF_FMC_OFF_MODE = 0x0B
    NDOF_MODE = 0x0C

imu_sensor = adafruit_bno055.BNO055_I2C(i2c)

# Set the sensor to NDOF_MODE
imu_sensor.mode = Mode.NDOF_MODE

def get_accelerometer_data():
    return np.array(imu_sensor.acceleration)

# Calibrate the accelerometer
print("Accelerometer: Perform the static calibration.")
calibration_positions = [
    "Place the sensor flat with the positive X-axis pointing up.",
    "Place the sensor flat with the negative X-axis pointing up.",
    "Place the sensor flat with the positive Y-axis pointing up.",
    "Place the sensor flat with the negative Y-axis pointing up.",
    "Place the sensor flat with the positive Z-axis pointing up.",
    "Place the sensor flat with the negative Z-axis pointing up."
]

measurements = []

for position in calibration_positions:
    input(f"{position} Press Enter when ready to record data...")
    time.sleep(2)  # Wait for the sensor to stabilize
    measurements.append(get_accelerometer_data())

# Calculate calibration offsets
measurements = np.array(measurements)
offsets = (measurements[0] + measurements[1] + measurements[2] + measurements[3] + measurements[4] + measurements[5]) / 6.0

print("Calibration offsets:", offsets)

# Apply offsets to accelerometer data
def apply_calibration(data):
    return data - offsets

# Calibrate the gyroscope
print("Gyroscope: Perform the hold-in-place calibration dance.")
print("Step 1: Place the sensor in a stable position on a flat surface.")
print("Step 2: Keep the sensor stationary for several seconds.")
while not imu_sensor.calibration_status[1] == 3:
    print(f"Gyro Calib Status: {100 / 3 * imu_sensor.calibration_status[1]:3.0f}%")
    time.sleep(5)
print("... Gyroscope CALIBRATED")

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
        while not tof_sensor.data_ready:
            if time.time() - timeout_start > timeout:
                print("Timeout waiting for sensor data.")
                break

        if tof_sensor.data_ready:
            tof_sensor.clear_interrupt()
            distance = tof_sensor.distance - tof_calibration

            # Get sensor data
            raw_accelerometer_data = imu_sensor.acceleration
            calibrated_accelerometer_data = apply_calibration(np.array(raw_accelerometer_data))
            magnetometer_data = imu_sensor.magnetic
            gyroscope_data = imu_sensor.gyro
            euler_data = imu_sensor.euler
            quaternion_data = imu_sensor.quaternion
            linear_acceleration_data = imu_sensor.linear_acceleration
            gravity_data = imu_sensor.gravity
            temperature = imu_sensor.temperature

            print(f"Distance: {distance} cm, Timestamp: {timestamp}")
            print(f"Sensor Data: Accelerometer (raw)={raw_accelerometer_data}, Accelerometer (calibrated)={calibrated_accelerometer_data}, Temperature={temperature}")

        # Wait for the remaining time until the next interval
        elapsed_time = time.time() - start_time
        remaining_time = interval - elapsed_time
        if remaining_time > 0:
            time.sleep(remaining_time)

        print("Temperature: {} degrees C".format(imu_sensor.temperature))
        print("Accelerometer (m/s^2): {}".format(calibrated_accelerometer_data))
        print("Magnetometer (microteslas): {}".format(imu_sensor.magnetic))
        print("Gyroscope (rad/sec): {}".format(imu_sensor.gyro))
        print("Euler angle: {}".format(imu_sensor.euler))
        print("Quaternion: {}".format(imu_sensor.quaternion))
        print("Linear acceleration (m/s^2): {}".format(imu_sensor.linear_acceleration))
        print("Gravity (m/s^2): {}".format(imu_sensor.gravity))
        print()
except KeyboardInterrupt:
    print("Program interrupted.")
