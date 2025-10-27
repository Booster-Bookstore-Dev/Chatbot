from flask import Flask, request, jsonify
from pymongo import MongoClient, errors
import os
import csv
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB connection setup
mongo_uri = os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/mydb")

print("Connecting to MongoDB...")
print(f"MONGO_URI: {mongo_uri}")

try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")  # Test connection
    print("✅ Connected to MongoDB successfully!")
except errors.ConnectionFailure as e:
    print("❌ MongoDB connection failed:", e)
    client = None

# Initialize DB and collection only if connection works
if client:
    db = client.get_database("mydb")
    collection = db["books"]
else:
    db = None
    collection = None

@app.route("/")
def home():
    return {"message": "Flask MongoDB API running!"}

@app.route("/books", methods=["GET"])
def get_books():
    if collection is None:
        return jsonify({"error": "Database not connected"}), 500
    books = list(collection.find({}, {"_id": 0}))
    return jsonify(books)

@app.route("/books", methods=["POST"])
def add_book():
    if collection is None:
        return jsonify({"error": "Database not connected"}), 500
    data = request.json
    if not data.get("title"):
        return jsonify({"error": "Missing 'title'"}), 400
    collection.insert_one(data)
    return jsonify({"message": "Book added successfully!"}), 201

@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    """
    Upload a CSV file to bulk insert records into MongoDB.
    Example: curl -X POST -F "file=@books.csv" http://localhost:6060/upload_csv
    """
    if collection is None:
        return jsonify({"error": "Database not connected"}), 500

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("utf-8"))
        csv_reader = csv.DictReader(stream)
        rows = list(csv_reader)

        if not rows:
            return jsonify({"error": "CSV file is empty"}), 400

        # Insert into MongoDB
        result = collection.insert_many(rows)
        return jsonify({
            "message": f"Successfully inserted {len(result.inserted_ids)} records!"
        }), 201

    except Exception as e:
        print("❌ CSV upload error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6060)
