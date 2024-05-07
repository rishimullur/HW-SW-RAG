import streamlit as st
import pandas as pd
import os

# Set the path to the directory containing the CSV file and images
data_dir = "/home/team13/Data-Gather"

# Read the CSV file
csv_path = os.path.join(data_dir, "sensor_data.csv")
data = pd.read_csv(csv_path)

# Function to display an image and its corresponding height value
def display_image_and_height(row):
    image_path = os.path.join(data_dir, row["Image Path"])
    st.image(image_path, use_column_width=True)
    st.write(f"Height: {row['Height (cm)']} cm")

# Streamlit app
st.title("Image and Height Viewer")

# Display the images and heights
for index, row in data.iterrows():
    st.subheader(f"Image {index + 1}")
    display_image_and_height(row)
    st.write("---")

