from flask import Flask, request, jsonify
from pymongo import MongoClient
import os
import dotenv

dotenv.load_dotenv()

app = Flask(__name__)
print("Connecting to MongoDB...")
print(f"MONGO_URI: {os.getenv('MONGO_URI')}")
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["mydb"]
collection = db["books"]

@app.route("/")
def home():
    return {"message": "Flask MongoDB API running!"}

@app.route("/books", methods=["GET"])
def get_books():
    books = list(collection.find({}, {"_id": 0}))
    return jsonify(books)

@app.route("/books", methods=["POST"])
def add_book():
    data = request.json
    if not data.get("title"):
        return jsonify({"error": "Missing 'title'"}), 400
    collection.insert_one(data)
    return jsonify({"message": "Book added successfully!"}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6060)
