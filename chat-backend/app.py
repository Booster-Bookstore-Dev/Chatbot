import os
import sys
import json
import requests
from dotenv import load_dotenv
import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from flask import Flask, request, jsonify

load_dotenv('./.env')

INDEX_PATH = os.getenv('INDEX_PATH', './data') 
INDEX_NAME = os.getenv('INDEX_NAME', 'faiss.index')
DATAFRAME_NAME = os.getenv('DATAFRAME_NAME', 'books.pkl')

#MAKE THESE IN .env
LLM_ENDPOINT = 'http://host.docker.internal:11434/api/chat'
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL',"qwen3:1.7b")


model = SentenceTransformer("all-MiniLM-L6-v2")
index = None
booksDataFrame= None

app = Flask(__name__)

def build_index():
    global index
    global booksDataFrame

    print("Fetching book data from db-backend...")
    try:
        # Fetch JSON from the db-backend service
        response = requests.get("http://db-backend:6060/books", timeout=10)
        response.raise_for_status()
        data = response.json()

        # Convert JSON list of dicts into a DataFrame
        booksDataFrame = pd.DataFrame(data)
        if booksDataFrame.empty:
            raise ValueError("Received empty book data from db-backend.")

        # Combine title and author text for vector embedding
        booksDataFrame['combined'] = (
            booksDataFrame["title"].astype(str) + " by " + booksDataFrame["authors"].astype(str)
        )

        # Save DataFrame for reuse
        os.makedirs(INDEX_PATH, exist_ok=True)
        booksDataFrame.to_pickle(os.path.join(INDEX_PATH, DATAFRAME_NAME))

        # Encode with SentenceTransformer
        embeddings = model.encode(booksDataFrame['combined'].tolist(), convert_to_numpy=True)
        dim = embeddings.shape[1]

        # Create and store FAISS index
        new_index = faiss.IndexFlatL2(dim)
        new_index.add(embeddings)
        faiss.write_index(new_index, os.path.join(INDEX_PATH, INDEX_NAME))

        index = new_index
        print("FAISS index built from db-backend data and loaded successfully.")

    except Exception as e:
        print(f"❌ Error fetching or building index: {e}", flush=True)
        sys.exit(1)

#This loads the index from our index location if it exists.
def load_index():
    global index
    index = faiss.read_index(INDEX_PATH + '/' + INDEX_NAME)
    print("Index reloaded.")
    
def load_data():
    global booksDataFrame
    booksDataFrame = pd.read_pickle(INDEX_PATH + "/" + DATAFRAME_NAME)
    print("Data Loaded")

def faiss_search(query:str, k=5):
    global index
    global booksDataFrame
    
    if not query:
        return -1
    
    query_vec=model.encode([query],convert_to_numpy=True)
    
    #Searches the index and returns the top 20 + k results
    D, I = index.search(query_vec, k=20+int(k))
    results = []
    
    #This sets the minimum results to 2 distinct results 
    for i, location in enumerate(I[0]):
        row=booksDataFrame.iloc[location]
        row = {
            "title": row["title"],
            "authors": row["authors"],
            "genres": row["genres"],
            "isbn": row["isbn"],
            "release_date": row["release_date"],
            "price": row["price"],
            "stock_count": row["stock_count"]
            
        }
        print(row, flush=True)
        #only adds distinct results (there are some repeats in the test dataset)
        if row not in results:
            results.append(row)
        if len(results) >= 2 and len(results) >= int(k):
            break
    return results


#LLM functions
def call_llm(messages, tools, stream):
    llm_response = requests.post(LLM_ENDPOINT, headers= { "Content-Type": "application/json" },
			json= {
				"model": OLLAMA_MODEL,
                "messages": messages,
                "tools": tools,
                "stream": stream,
                })
    data = llm_response.json()
    print(data, flush=True)
    assistant_msg = data["message"]
    messages.append(assistant_msg)
    
    if "tool_calls" in assistant_msg:
        print("Book_Search called", flush=True)
        print(assistant_msg, flush=True)
        for call in assistant_msg["tool_calls"]:
            if call["function"]["name"] == "book_search":
                if call["function"]["arguments"]["query"]:
                    args = call["function"]["arguments"]
                    tool_result = faiss_search(args["query"], args["numberOfBooks"])
                    # Append tool output to the chat history
                    tool_output= set({})
                    for result in tool_result:
                        tool_output.add(result["title"] +" by " +result["authors"] + " (Genres: " + result["genres"] + ", ISBN: " + str(result["isbn"])+ ", Release Date: " + str(result["release_date"])+ ", Price: $" + str(result["price"])+ ", Stock Count: " + str(result["stock_count"])+")")
                    print(tool_output)
                    messages.append({
                        "role": "tool",
                        "content": str(tool_result),
                        "tool_name": "book_search"
                    })
                    return call_llm(messages,[tools[1]],stream)
            if call["function"]["arguments"]["reply"]:
                messages.append({"role": "assistant", "content" : call["function"]["arguments"]["reply"]})
                print(json.dumps(messages,indent=4), flush=True)
                return messages
    else:
        print(assistant_msg, flush=True)
        reply = assistant_msg["content"]
        if "</think>" in reply:
            end_index = reply.index("</think>")
            reply = reply[end_index+9:]
            print(reply, flush=True)
            #I want to return messages
        return reply


#Routes

@app.route("/rebuild_index", methods=["POST"])
def rebuild_index_api():
    build_index()  # rebuild and reload immediately
    return jsonify({"status": "index rebuilt"})

#Temporary API to test the faiss search
@app.route("/search", methods=["POST"])
def search_api():
    data = request.json or {}
    query = data.get("query", "")
    k = data.get("k", 5)
    if not query:
        return jsonify({"error": "No query provided"}), 400
    response = faiss_search(query, k)
    return jsonify(response)

@app.route("/chat", methods=["POST"])
def llm_chat():
    req_data = request.json or {}
    user_message = req_data.get("message", "")
    history = req_data.get("history", False)
    if not user_message:
        return jsonify({"error": "No message provided"})
    if not history:
        messages = [
            {
                "role": "system",
                "content": """/no_think 
                    You are a bookstore assistant. 
                    - Use the `book_search` tool only when the user explicitly requests books, or when you must fetch book data. 
                    - Use the `reply` tool to send your response to the user.
                    - Return exactly the number of books the user asks for, no more. 
                    - Keep replies concise and direct. 
                    - When asked for similar books, exclude any with the same title as the reference. 
                    - Do not explain your reasoning or mention tools in responses.
                    - If user asks for books sorted, rearrange them to sort them by how the user asks (Alphabetical, by rating, or other)."""
            },
            {
                'role': 'user',
                'content': user_message
            }
        ]
    else:
        messages = history + [{'role': 'user', 'content': user_message }]
    
    tools=[{
        
        "type": "function",
            "function": {
                "name": "book_search",
                "description": "Searches the bookstore database for book titles and authors using semantic search on 'query'. Returns a list of books in no particular order. Choose only the most applicable ones. Request more than one for similarity searches so it doesn't return a the original book. ",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search terms that should be used to find a book for the user."
                        },
                        "numberOfBooks": {
                            "type": "integer",
                            "description": "The number of books that you want returned"
                        }
                    },
                    "required": ["query"]
                }
            }
    },
        {
        "type": "function",
            "function": {
                "name": "reply",
                "description": "Sends the imput to the user as a reply to their question. Use if you do not need any other tools.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reply": {
                            "type": "string",
                            "description": "Reply to send to the user."
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    return jsonify(call_llm(messages, tools, False))
    # updated_messages = call_llm(messages, tools, False)
    
    
    
    
if __name__ == "__main__":
    # Load existing index if it exists
    if os.path.exists(INDEX_PATH + '/' + INDEX_NAME) and os.path.exists(INDEX_PATH + "/" + DATAFRAME_NAME):
        load_index()
        load_data()
    else:
        build_index()

    app.run(host="0.0.0.0", port=5050)
