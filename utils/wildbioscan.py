import board
import adafruit_vl53l4cd
import time
import os
import subprocess
import firebase_admin
import adafruit_bno055
from firebase_admin import credentials, storage, db
import os
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

#pip3 install firebase-admin

# Initialize Firebase Admin SDK using the environment variables
cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
database_url = os.getenv('FIREBASE_DATABASE_URL')
storage_bucket = os.getenv('FIREBASE_STORAGE_BUCKET')

cred = credentials.Certificate(cred_path)
app = firebase_admin.initialize_app(cred, {
    'databaseURL': database_url,
    'storageBucket': storage_bucket
})
bucket = storage.bucket()

i2c = board.I2C()
vl53 = adafruit_vl53l4cd.VL53L4CD(i2c)
sensor = adafruit_bno055.BNO055_I2C(i2c)
calibration_val = 1.5
timeout = 0.5  # Timeout in seconds
interval = 5   # Interval in seconds

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
        while not vl53.data_ready:
            if time.time() - timeout_start > timeout:
                print("Timeout waiting for sensor data.")
                break

        if vl53.data_ready:
            vl53.clear_interrupt()
            distance = vl53.distance - calibration_val

            # Get sensor data
            accelerometer_data = (sensor.acceleration)
            magnetometer_data = (sensor.magnetic)
            gyroscope_data = (sensor.gyro)
            euler_data = (sensor.euler)
            quaternion_data = (sensor.quaternion)
            linear_acceleration_data = (sensor.linear_acceleration)
            gravity_data = (sensor.gravity)
            temperature = (sensor.temperature)

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
        

        print("Temperature: {} degrees C".format(sensor.temperature))
        """
        print(
            "Temperature: {} degrees C".format(temperature())
        )  # Uncomment if using a Raspberry Pi
        """
        print("Accelerometer (m/s^2): {}".format(sensor.acceleration))
        print("Magnetometer (microteslas): {}".format(sensor.magnetic))
        print("Gyroscope (rad/sec): {}".format(sensor.gyro))
        print("Euler angle: {}".format(sensor.euler))
        print("Quaternion: {}".format(sensor.quaternion))
        print("Linear acceleration (m/s^2): {}".format(sensor.linear_acceleration))
        print("Gravity (m/s^2): {}".format(sensor.gravity))
    print()
except KeyboardInterrupt:
    print("Program interrupted.")


