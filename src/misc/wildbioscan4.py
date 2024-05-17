import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from rplidar import RPLidar
import board
import busio
import adafruit_vl53l4cd
import adafruit_bno055
import time
import os
import subprocess
import firebase_admin
from firebase_admin import credentials, storage, db
from dotenv import load_dotenv

# Load environment variables
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
lidar = RPLidar('/dev/ttyUSB0')

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

def get_orientation():
    """Get the orientation (yaw, pitch, roll) from the BNO055 sensor."""
    if imu_sensor.euler:
        yaw, roll, pitch = imu_sensor.euler
        return yaw, pitch, roll
    return 0, 0, 0  # Default to 0s if no data is available

def polar_to_3D(distance, angle, yaw, pitch):
    """Convert polar coordinates to 3D coordinates."""
    angle_rad = np.radians(angle + yaw)
    pitch_rad = np.radians(pitch)
    x = distance * np.cos(angle_rad) * np.cos(pitch_rad)
    y = distance * np.sin(angle_rad) * np.cos(pitch_rad)
    z = distance * np.sin(pitch_rad)
    return x, y, z

def collect_data():
    """Collects data from all sensors if image capture is successful."""
    # Collect LiDAR data
    point_cloud = []
    yaw, pitch, roll = get_orientation()
    for _, angle, distance in next(lidar.iter_scans()):
        if distance > 0:
            x, y, z = polar_to_3D(distance, angle, yaw, pitch)
            point_cloud.append((x, y, z))

    # Wait for TOF sensor data or timeout
    timeout_start = time.time()
    while not tof_sensor.data_ready:
        if time.time() - timeout_start > TIMEOUT:
            print("Timeout waiting for TOF sensor data.")
            break

    if tof_sensor.data_ready:
        tof_sensor.clear_interrupt()
        distance = tof_sensor.distance - TOF_CALIBRATION
        timestamp = time.time()
        # Get sensor data
        accelerometer_data = imu_sensor.acceleration
        magnetometer_data = imu_sensor.magnetic
        gyroscope_data = imu_sensor.gyro
        euler_data = imu_sensor.euler
        quaternion_data = imu_sensor.quaternion
        linear_acceleration_data = imu_sensor.linear_acceleration
        gravity_data = imu_sensor.gravity
        temperature = imu_sensor.temperature
        return {
            "Timestamp": timestamp,
            "Height (cm)": distance,
            "Accelerometer (ms^2)": accelerometer_data,
            "Magnetometer (microteslas)": magnetometer_data,
            "Gyroscope (radsec)": gyroscope_data,
            "Euler angle": euler_data,
            "Quaternion": quaternion_data,
            "Linear acceleration (ms^2)": linear_acceleration_data,
            "Gravity (ms^2)": gravity_data,
            "Temperature (degrees C)": temperature
        }, point_cloud
    return {}, point_cloud

def log_data(data, image_url, point_cloud):
    """Log sensor data and point cloud to Firebase."""
    ref = db.reference('sensor_data_latest')
    new_data_ref = ref.push()
    data["image_url"] = image_url
    data["point_cloud"] = point_cloud
    new_data_ref.set(data)

def visualize_point_cloud(point_cloud):
    """Visualize the 3D point cloud collected from LiDAR."""
    if point_cloud:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        xs, ys, zs = zip(*point_cloud)
        ax.scatter(xs, ys, zs, s=1)
        ax.set_xlabel('X (cm)')
        ax.set_ylabel('Y (cm)')
        ax.set_zlabel('Z (cm)')
        plt.show()

try:
    while True:
        start_time = time.time()
        output_path = os.path.join(os.getcwd(), f"image_{int(time.time())}.jpg")
        
        if capture_image(output_path):
            image_url = upload_image(output_path)
            sensor_data, point_cloud = collect_data()
            log_data(sensor_data, image_url, point_cloud)
            visualize_point_cloud(point_cloud)  # Visualize point cloud
            print("Point cloud visualization completed.")
            
            # Display collected data
            print(f"Sensor Data: {sensor_data}")
            print(f"TOF Distance: {sensor_data['Height (cm)']} cm")
            print(f"Temperature: {sensor_data['Temperature (degrees C)']} degrees C")
            print(f"Accelerometer: {sensor_data['Accelerometer (ms^2)']}")
            print(f"Magnetometer: {sensor_data['Magnetometer (microteslas)']}")
            print(f"Gyroscope: {sensor_data['Gyroscope (radsec)']}")
            print(f"Euler angles: {sensor_data['Euler angle']}")
            print(f"Quaternion: {sensor_data['Quaternion']}")
            print(f"Linear acceleration: {sensor_data['Linear acceleration (ms^2)']}")
            print(f"Gravity: {sensor_data['Gravity (ms^2)']}")
            print(f"Image URL: {image_url}")

        else:
            print("Image capture failed, skipping sensor and LiDAR reading.")

        time_to_sleep = INTERVAL - (time.time() - start_time)
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)
except KeyboardInterrupt:
    print("Program interrupted.")
except Exception as e:
    print(f"Unexpected error: {str(e)}")
finally:
    lidar.stop()
    lidar.disconnect()
