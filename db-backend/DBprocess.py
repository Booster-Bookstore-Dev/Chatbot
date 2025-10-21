mport os
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.errors import DuplicateKeyError
from rapidfuzz import process, fuzz

# -----------------------------
# Env & Mongo
# -----------------------------
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "library")
BOOKS_COLL = os.getenv("BOOKS_COLL", "books")
FAQ_COLL = os.getenv("FAQ_COLL", "faqs")
USE_ATLAS_SEARCH = os.getenv("USE_ATLAS_SEARCH", "true").lower() == "true"

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is required (set it in .env).")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
books = db[BOOKS_COLL]
faqs = db[FAQ_COLL]

# -----------------------------
# Index helpers
# -----------------------------
def ensure_indexes():
    # For dedupe: title+author+isbn (isbn can be absent)
    try:
        books.create_index(
            [("title", ASCENDING), ("author", ASCENDING), ("isbn", ASCENDING)],
            unique=True,
            name="uniq_title_author_isbn"
        )
    except Exception:
        pass

    # Fallback text index when Atlas Search is off
    # (do NOT mix with $search, it's only for fallback)
    try:
        books.create_index(
            [
                ("title", TEXT),
                ("author", TEXT),
                ("description", TEXT),
                ("tags", TEXT),
            ],
            name="books_text_idx"
        )
    except Exception:
        pass

    # FAQs: unique question
    try:
        faqs.create_index([("question", ASCENDING)], unique=True, name="uniq_question")
    except Exception:
        pass

ensure_indexes()

# -----------------------------
# FAQ fuzzy store (cached view)
# -----------------------------
class FAQStore:
    def __init__(self):
        self._refresh()

    def _refresh(self):
        docs = list(faqs.find({}, {"_id": 0, "question": 1, "answer": 1}))
        self._q_to_a = {d["question"]: d["answer"] for d in docs}
        self._norm_map = {self._norm(q): q for q in self._q_to_a.keys()}

    @staticmethod
    def _norm(text: str) -> str:
        return " ".join(text.lower().strip().split())

    def answer(self, question: str, threshold: int = 75):
        if not question.strip() or not self._q_to_a:
            return None
        match, score, _ = process.extractOne(
            self._norm(question),
            list(self._norm_map.keys()),
            scorer=fuzz.token_set_ratio
        )
        if score >= threshold:
            canonical_q = self._norm_map[match]
            return {"question": canonical_q, "answer": self._q_to_a[canonical_q], "confidence": score}
        return None

FAQ_STORE = FAQStore()

# Seed default FAQs (idempotent)
DEFAULT_FAQS = [
    {"question": "What are your business hours?", "answer": "We’re available 9am–5pm PT, Monday–Friday."},
    {"question": "How do I reset my password?", "answer": "Use ‘Forgot password’ on the sign-in page; check your email link."},
    {"question": "Do you offer refunds?", "answer": "Yes—within 30 days for undamaged items with a receipt."},
    {"question": "How long does shipping take?", "answer": "Most orders arrive in 3–7 business days in the U.S."},
]
for faq in DEFAULT_FAQS:
    try:
        faqs.insert_one(faq)
    except DuplicateKeyError:
        pass
FAQ_STORE._refresh()

# -----------------------------
# Search with Atlas Search (fallback to regex/text)
# -----------------------------
def atlas_search_pipeline(query: str, limit: int) -> List[Dict[str, Any]]:
    """
    Requires an Atlas Search index (e.g., named 'default') configured over fields:
    title, author, isbn, description, tags
    """
    pipeline = [
        {
            "$search": {
                "index": "default",  # change if your index name differs
                "compound": {
                    "should": [
                        {"text": {"query": query, "path": ["title", "author"], "score": {"boost": {"value": 4}}}},
                        {"text": {"query": query, "path": ["description", "tags"], "score": {"boost": {"value": 2}}}},
                        {"autocomplete": {"query": query, "path": "title", "tokenOrder": "sequential", "score": {"boost": {"value": 6}}}},
                    ],
                }
            }
        },
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "id": "$_id",
                "title": 1,
                "author": 1,
                "isbn": 1,
                "description": 1,
                "tags": 1,
                "score": {"$meta": "searchScore"},
                "highlights": {"$meta": "searchHighlights"},
            }
        }
    ]
    return list(books.aggregate(pipeline))

def fallback_search(query: str, limit: int) -> List[Dict[str, Any]]:
    # Prefer $text when index exists; else regex OR logic
    results: List[Dict[str, Any]] = []
    try:
        # $text
        cursor = books.find(
            {"$text": {"$search": query}},
            {
                "_id": 0,
                "id": "$_id",
                "title": 1,
                "author": 1,
                "isbn": 1,
                "description": 1,
                "tags": 1,
                "score": {"$meta": "textScore"},
            },
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        results = list(cursor)
    except Exception:
        pass

    if not results:
        # regex fallback across common fields (case-insensitive)
        rx = {"$regex": query, "$options": "i"}
        cursor = books.find(
            {"$or": [{"title": rx}, {"author": rx}, {"description": rx}, {"tags": rx}]},
            {"_id": 0, "id": "$_id", "title": 1, "author": 1, "isbn": 1, "description": 1, "tags": 1},
        ).limit(limit)
        results = list(cursor)
    return results

def search_books(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    if not query.strip():
        return []
    if USE_ATLAS_SEARCH:
        try:
            hits = atlas_search_pipeline(query, limit)
            if hits:
                return hits
        except Exception:
            # silently fall back if Atlas Search not configured
            pass
    return fallback_search(query, limit)

# -----------------------------
# FastAPI
# -----------------------------
app = FastAPI(title="Chatbot Backend (PyMongo: FAQ + Book Search)")

class SearchBody(BaseModel):
    query: str
    limit: int = 10

class FAQBody(BaseModel):
    question: str

class ChatBody(BaseModel):
    message: str
    limit: int = 10

BOOK_KEYWORDS = {"book", "title", "author", "isbn", "novel", "read", "library", "search"}

def is_book_intent(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in BOOK_KEYWORDS)

@app.post("/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV and upsert into MongoDB.
    Required columns: title, author
    Optional: isbn, description, tags
    """
    tmp = Path(f"_upload_{file.filename}")
    with open(tmp, "wb") as f:
        f.write(await file.read())

    df = pd.read_csv(tmp)
    for col in ["title", "author", "isbn", "description", "tags"]:
        if col not in df.columns:
            df[col] = ""

    # Upsert rows based on (title, author, isbn)
    to_ops = []
    for row in df.itertuples(index=False):
        doc = {
            "title": str(getattr(row, "title", "")).strip(),
            "author": str(getattr(row, "author", "")).strip(),
            "isbn": str(getattr(row, "isbn", "")).strip(),
            "description": str(getattr(row, "description", "")).strip(),
            "tags": str(getattr(row, "tags", "")).strip(),
        }
        if not doc["title"] and not doc["author"]:
            continue
        to_ops.append(
            {
                "updateOne": {
                    "filter": {
                        "title": doc["title"],
                        "author": doc["author"],
                        "isbn": doc["isbn"],
                    },
                    "update": {"$set": doc},
                    "upsert": True,
                }
            }
        )

    inserted = 0
    if to_ops:
        res = books.bulk_write(to_ops, ordered=False)
        # inserted count approximation (Mongo returns upserted ids separately)
        inserted = (res.upserted_count or 0) + (res.modified_count or 0)

    tmp.unlink(missing_ok=True)
    return {"status": "ok", "processed": inserted}

@app.post("/search")
def api_search(body: SearchBody):
    return {"results": search_books(body.query, body.limit)}

@app.post("/faq")
def api_faq(body: FAQBody):
    ans = FAQ_STORE.answer(body.question)
    return {"answer": ans}

@app.post("/chat")
def api_chat(body: ChatBody):
    text = body.message.strip()
    if is_book_intent(text):
        return {"type": "book_search", "results": search_books(text, body.limit)}
    ans = FAQ_STORE.answer(text)
    if ans:
        return {"type": "faq", "answer": ans}
    return {"type": "fallback", "message": "I couldn’t find an answer. Try rephrasing or include a book title/author."}

@app.post("/faq/upsert_defaults")
def api_faq_upsert_defaults():
    # Handy endpoint to ensure the default FAQs exist in DB (idempotent)
    added = 0
    for faq in DEFAULT_FAQS:
        try:
            faqs.insert_one(faq)
            added += 1
        except DuplicateKeyError:
            pass
    FAQ_STORE._refresh()
    return {"status": "ok", "added": added}

# For local dev
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_mongo:app", host="0.0.0.0", port=5051, reload=True)
