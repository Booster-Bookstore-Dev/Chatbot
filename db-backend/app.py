from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient, errors
import os
import csv
import io
import requests
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

# Initialize DB and collection
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


@app.route("/manage")
def manage_page():
    return render_template("manage.html")

@app.route("/manage/upload_books", methods=["POST"])  # Add /manage prefix
def upload_books():
    """
    Upload CSV with option to replace or append.
    """
    if collection is None:
        return jsonify({"error": "Database not connected"}), 500

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    mode = request.form.get("mode", "append")

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8"))
        csv_reader = csv.DictReader(stream)
        rows = list(csv_reader)

        if not rows:
            return jsonify({"error": "CSV file is empty"}), 400

        if mode == "replace":
            collection.delete_many({})
            print("⚠️ Replaced existing books with new data.")

        result = collection.insert_many(rows)
        return jsonify({
            "message": f"Successfully inserted {len(result.inserted_ids)} records! (Mode: {mode})"
        }), 201

    except Exception as e:
        print("❌ CSV upload error:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/manage/rebuild_index", methods=["POST"])  # Add /manage prefix
def rebuild_index():
    """
    Send a POST request to chat-backend:5050/rebuild_index
    """
    try:
        response = requests.post("http://chat-backend:5050/rebuild_index", timeout=10)
        if response.status_code == 200:
            return jsonify({"message": "Rebuild triggered successfully!"}), 200
        else:
            return jsonify({"error": f"Rebuild failed: {response.text}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6060)
