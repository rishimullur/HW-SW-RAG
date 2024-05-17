import time
import board
import os
import subprocess
import firebase_admin
import adafruit_vl53l4cd
import adafruit_bno055
from firebase_admin import credentials, storage, db
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Firebase setup
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL'),
    'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
})
bucket = storage.bucket()

# Sensor initialization
i2c = board.I2C()
tof_sensor = adafruit_vl53l4cd.VL53L4CD(i2c)
tof_sensor.start_ranging()
imu_sensor = adafruit_bno055.BNO055_I2C(i2c)
imu_sensor.mode = 0x0C  # NDOF mode

# Constants
TOF_CALIBRATION = 1.5
TIMEOUT = 0.5  # seconds
INTERVAL = 5   # seconds

def capture_image(output_path):
    """Capture an image using the Raspberry Pi camera."""
    try:
        cmd = f"libcamera-still --output {output_path} --timeout 5000 --tuning-file /usr/share/libcamera/ipa/rpi/pisp/imx519.json"
        subprocess.run(cmd, shell=True, check=True)
        print(f"Image captured and saved as {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Camera command failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"Error capturing image: {str(e)}")
        return False

def upload_image(image_path):
    """Upload an image to Firebase storage and return the public URL."""
    blob = bucket.blob(os.path.basename(image_path))
    blob.upload_from_filename(image_path, content_type='image/jpeg')
    return blob.public_url

def read_sensors():
    """Read all sensor data and return as a dictionary."""
    sensor_data = {}
    if not tof_sensor.data_ready and time.time() - start_time > TIMEOUT:
        print("Timeout waiting for TOF sensor data.")
        sensor_data['distance'] = None
    else:
        distance = tof_sensor.distance - TOF_CALIBRATION
        sensor_data['distance'] = f"{distance:.2f} cm"

    sensor_data['accelerometer'] = imu_sensor.acceleration if imu_sensor.acceleration else "No Data"
    sensor_data['magnetometer'] = imu_sensor.magnetic if imu_sensor.magnetic else "No Data"
    sensor_data['gyroscope'] = imu_sensor.gyro if imu_sensor.gyro else "No Data"
    sensor_data['euler'] = imu_sensor.euler if imu_sensor.euler else "No Data"
    sensor_data['quaternion'] = imu_sensor.quaternion if imu_sensor.quaternion else "No Data"
    sensor_data['linear_acceleration'] = imu_sensor.linear_acceleration if imu_sensor.linear_acceleration else "No Data"
    sensor_data['gravity'] = imu_sensor.gravity if imu_sensor.gravity else "No Data"
    sensor_data['temperature'] = imu_sensor.temperature if imu_sensor.temperature else "No Data"
    
    return sensor_data

def log_data(data, image_url):
    """Log sensor data to Firebase."""
    ref = db.reference('sensor_data_latest')
    new_data_ref = ref.push()
    data["image_url"] = image_url
    new_data_ref.set(data)

try:
    while True:
        start_time = time.time()
        output_path = os.path.join(os.getcwd(), f"image_{int(time.time())}.jpg")
        
        if capture_image(output_path):
            image_url = upload_image(output_path)
            sensor_data = read_sensors()
            log_data(sensor_data, image_url)

            # Print sensor data for visual verification
            for key, value in sensor_data.items():
                print(f"{key}: {value}")
        else:
            print("Image capture failed, skipping sensor reading.")

        time_to_sleep = INTERVAL - (time.time() - start_time)
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)
except KeyboardInterrupt:
    print("Program interrupted.")
except Exception as e:
    print(f"Unexpected error: {str(e)}")
