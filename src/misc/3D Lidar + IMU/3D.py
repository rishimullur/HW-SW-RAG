import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from rplidar import RPLidar
import board
import busio
import adafruit_bno055
import time

# Initialize RPLidar
lidar = RPLidar('/dev/ttyUSB0')

# Initialize BNO055
i2c = board.I2C()  # uses board.SCL and board.SDA
sensor = adafruit_bno055.BNO055_I2C(i2c)

def get_orientation():
    """ Get the orientation (yaw, pitch, roll) from the BNO055 sensor. """
    if sensor.euler:
        yaw, roll, pitch = sensor.euler  # Adjust these based on your mounting configuration
        return yaw, pitch, roll
    return 0, 0, 0  # Default to 0s if no data is available

def polar_to_3D(distance, angle, yaw, pitch):
    """ Convert polar coordinates to 3D coordinates. """
    angle_rad = np.radians(angle + yaw)
    pitch_rad = np.radians(pitch)
    x = distance * np.cos(angle_rad) * np.cos(pitch_rad)
    y = distance * np.sin(angle_rad) * np.cos(pitch_rad)
    z = distance * np.sin(pitch_rad)
    return x, y, z

def main():
    point_cloud = []

    try:
        print("Collecting data...")
        for i, scan in enumerate(lidar.iter_scans(scan_type="express")):
            yaw, pitch, roll = get_orientation()
            for (_, angle, distance) in scan:
                if distance > 0:  # Filter out invalid readings
                    x, y, z = polar_to_3D(distance, angle, yaw, pitch)
                    point_cloud.append((x, y, z))
            if i > 10:  # Collect a few scans then stop
                break
    except KeyboardInterrupt:
        print("Stopping.")
    lidar.stop()
    lidar.disconnect()

    # Visualization
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    if point_cloud:
        xs, ys, zs = zip(*point_cloud)
        ax.scatter(xs, ys, zs, s=1)
    plt.show()

if __name__ == '__main__':
    main()
