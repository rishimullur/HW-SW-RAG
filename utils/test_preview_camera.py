import os
import subprocess

# Specify the folder paths
folder_path_1 = "/home/team13/LeptonModule/software/raspberrypi_video"
folder_path_2 = "/home/team13/Desktop"


try:
    # Change the current working directory to the first specified folder
    os.chdir(folder_path_1)
except FileNotFoundError:
    print(f"Error: The folder '{folder_path_1}' does not exist.")
except PermissionError:
    print(f"Error: You don't have permission to access the folder '{folder_path_1}'.")
except Exception as e:
    print(f"Error: An unexpected error occurred: {e}")
else:
    try:
        print("Lepton camera starting...")
        # Run the first shell command in a separate process
        process_1 = subprocess.Popen(["./raspberrypi_video", "-tl", "3"])
    except FileNotFoundError:
        print("Error: The 'raspberrypi_video' file does not exist in the current directory.")
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")

try:
    # Change the current working directory to the second specified folder
    os.chdir(folder_path_2)
except FileNotFoundError:
    print(f"Error: The folder '{folder_path_2}' does not exist.")
except PermissionError:
    print(f"Error: You don't have permission to access the folder '{folder_path_2}'.")
except Exception as e:
    print(f"Error: An unexpected error occurred: {e}")
else:
    try:
        print("Camera starting up...")
        # Run the second shell command in a separate process
        process_2 = subprocess.Popen(["python3", "Test_Cam.py"])
    except FileNotFoundError:
        print("Error: The 'Test_Cam.py' file does not exist in the current directory.")
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")

process_1.wait()
print(f"Process 1 exit code: {process_1.returncode}")

process_2.wait()
print(f"Process 2 exit code: {process_2.returncode}")
