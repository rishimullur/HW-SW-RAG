import board
import adafruit_vl53l4cd
import time
import os
import subprocess
import firebase_admin
import adafruit_bno055
import busio
from dotenv import load_dotenv
from firebase_admin import credentials, storage, db # Only for cloud demo

# Load environment variables from .env file
load_dotenv()

# Cloud demo only - Initialize Firebase Admin SDK using the environment variables
cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
database_url = os.getenv('FIREBASE_DATABASE_URL')
storage_bucket = os.getenv('FIREBASE_STORAGE_BUCKET')

cred = credentials.Certificate(cred_path)
app = firebase_admin.initialize_app(cred, {
    'databaseURL': database_url,
    'storageBucket': storage_bucket
})
bucket = storage.bucket()

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


time.sleep(5)
print("Gyroscope: Perform the hold-in-place calibration dance.")
while not imu_sensor.calibration_status[1] == 3:
    # Calibration Dance Step Three: Gyroscope
    # Place sensor in any stable position for a few seconds
    print(f"Gyro Calib Status: {100 / 3 * imu_sensor.calibration_status[1]:3.0f}%")
    time.sleep(5)
print("... CALIBRATED")

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

def format_tuple(data):
    if data is None:
        return None
    return ', '.join(map(str, data))  # Convert tuple to comma-separated string

def sanitize_data(data):
    if data is None:
        return None
    # Replace any forbidden characters with an underscore
    return str(data).replace('$', '_').replace('#', '_').replace('[', '_').replace(']', '_').replace('/', '_').replace('.', '_')

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

        # Upload image to Firebase Storage
        blob = bucket.blob(output_filename)
        with open(output_path, "rb") as image_file:
            blob.upload_from_file(image_file, content_type='image/jpeg') 

        # Get the public URL of the uploaded image
        image_url = blob.public_url

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
            accelerometer_data = (imu_sensor.acceleration)
            magnetometer_data = (imu_sensor.magnetic)
            gyroscope_data = (imu_sensor.gyro)
            euler_data = (imu_sensor.euler)
            quaternion_data = (imu_sensor.quaternion)
            linear_acceleration_data = (imu_sensor.linear_acceleration)
            gravity_data = (imu_sensor.gravity)
            temperature = (imu_sensor.temperature)

            # Write the data to the Firebase Realtime Database
            ref = db.reference('sensor_data_latest')
            new_data_ref = ref.push()
            new_data_ref.set({
                "Timestamp": timestamp,
                "Height (cm)": distance,
                "Image URL": image_url,
                "Accelerometer (ms^2)": accelerometer_data,
                "Magnetometer (microteslas)": magnetometer_data,
                "Gyroscope (radsec)": gyroscope_data,
                "Euler angle": euler_data,
                "Quaternion": quaternion_data,
                "Linear acceleration (ms^2)": linear_acceleration_data,
                "Gravity (ms^2)": gravity_data,
                "Temperature (degrees C)": temperature
            })

            print(f"Distance: {distance} cm, Timestamp: {timestamp}, Image URL: {image_url}")
            print(f"Sensor Data: Accelerometer={accelerometer_data}, Temperature={temperature}")

        # Wait for the remaining time until the next interval
        elapsed_time = time.time() - start_time
        remaining_time = interval - elapsed_time
        if remaining_time > 0:
            time.sleep(remaining_time)
        

        print("Temperature: {} degrees C".format(imu_sensor.temperature))
        """
        print(
            "Temperature: {} degrees C".format(temperature())
        )  # Uncomment if using a Raspberry Pi
        """
        print("Accelerometer (m/s^2): {}".format(imu_sensor.acceleration))
        print("Magnetometer (microteslas): {}".format(imu_sensor.magnetic))
        print("Gyroscope (rad/sec): {}".format(imu_sensor.gyro))
        print("Euler angle: {}".format(imu_sensor.euler))
        print("Quaternion: {}".format(imu_sensor.quaternion))
        print("Linear acceleration (m/s^2): {}".format(imu_sensor.linear_acceleration))
        print("Gravity (m/s^2): {}".format(imu_sensor.gravity))
    print()
except KeyboardInterrupt:
    print("Program interrupted.")
