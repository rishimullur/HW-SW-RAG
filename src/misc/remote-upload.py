import csv
import firebase_admin
from firebase_admin import credentials, storage, db

# Initialize the Firebase Admin SDK
cred = credentials.Certificate("/home/team13/Data-Gather/wildbioscan-f4ef16a1637f.json")
app = firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://wildbioscan-default-rtdb.firebaseio.com/',
    'storageBucket': 'wildbioscan.appspot.com'
})

# Get a reference to the storage service
bucket = storage.bucket(app=app)

# Get a reference to the database
ref = db.reference('data')

# Open the CSV file
with open('/home/team13/Data-Gather/sensor_data.csv', 'r') as csv_file:
    csv_reader = csv.reader(csv_file)
    next(csv_reader)  # Skip the header row

    # Iterate over each row in the CSV
    for row in csv_reader:
        timestamp = row[0]
        height = row[1]
        image_path = row[2]

        # Upload the image file to Firebase Storage
        blob = bucket.blob(image_path)
        blob.upload_from_filename(image_path)

        # Make the blob publicly viewable
        blob.make_public()

        # Get the public URL of the blob
        image_url = blob.public_url

        # Save the metadata to Firebase Realtime Database
        data = {
            'timestamp': timestamp,
            'height': height,
            'imageUrl': image_url  # URL of the image in the storage bucket
        }
        ref.push().set(data)

