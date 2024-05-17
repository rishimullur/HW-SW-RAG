import os
import subprocess

# Define the necessary paths
venv_path = "/home/team13/RPLIDAR/env/bin/activate"
script_dir = "/home/team13/RPLIDAR/RPLidar/examples"
script_name = "lidar_test_demo_v1.py"

# # Activate the virtual environment
# activate_env = f". {venv_path}; exec $SHELL -l"
# venv_subprocess = subprocess.Popen(activate_env, shell=True, executable="/bin/bash", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# # Wait for the virtual environment to activate
# venv_subprocess.wait()

# Navigate to the script directory
os.chdir(script_dir)

# Run the script in the activated virtual environment
subprocess.run(["python3", script_name], shell=True, executable="/bin/bash")