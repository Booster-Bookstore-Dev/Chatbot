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
DATA_PATH = os.getenv('DATA_PATH', './start_data')

#MAKE THESE IN .env
LLM_ENDPOINT = 'http://ollama:11434/api/chat'
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL',"qwen3:1.7b")


model = SentenceTransformer("all-MiniLM-L6-v2")
index = None
booksDataFrame= None

app = Flask(__name__)


# Index functions
def build_index():
    # Builds the FAISS index and loads it into memory
    global index
    global booksDataFrame
    print("Building FAISS index...")
    #Reads data from csv and stores in a pandas Data Frame
    booksDataFrame = pd.read_csv(DATA_PATH + '/data.csv', on_bad_lines='warn')
    #Creates a combined list of the 
    booksDataFrame['combined'] = booksDataFrame["title"].astype(str) + " by " + booksDataFrame["authors"].astype(str)
    #outputs the dataframe to a pickle file
    os.makedirs(INDEX_PATH, exist_ok=True)
    booksDataFrame.to_pickle(INDEX_PATH + "/" + DATAFRAME_NAME)
    #Encodes using the LLM specified above to create vectors for the combined list in the Data Frame
    embeddings = model.encode(booksDataFrame['combined'].astype(str).tolist(), convert_to_numpy=True)
    #Finds out how many dimensions there are in the matrix
    dim = embeddings.shape[1]
    #Creates an empty flat index with the number of dimensions in our embeddings
    new_index = faiss.IndexFlatL2(dim)
    #adds our embeddings (dim # of dimension vectors) to the index we just created
    new_index.add(embeddings)
    
    #makes the index path if it doesnt exist 
    
    #uses the faiss library to write the index with index name to index path
    faiss.write_index(new_index, INDEX_PATH + '/' + INDEX_NAME)
    #sets global index to the new index we just created
    index = new_index
    print("FAISS index built and loaded.")

#This loads the index from our index loacation if it exists.
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
    D, I = index.search(query_vec, k=20+k)
    results = []
    
    #This sets the minimum results to 2 distinct results 
    for i, location in enumerate(I[0]):
        row=booksDataFrame.iloc[location]
        row = {
            "title": row["title"],
            "authors": row["authors"],
            "average_rating": row["average_rating"]
        }
        print(row, flush=True)
        #only adds distinct results (there are some repeats in the test dataset)
        if row not in results:
            results.append(row)
        if len(results) >= 2 and len(results) >=k:
            break
    return results


#LLM functions
def call_llm(messages, tools, stream):
    try:
        llm_res = requests.post(LLM_ENDPOINT,headers= { "Content-Type": "application/json" },
			json= {
				"model": OLLAMA_MODEL,
                "messages": messages,
                "tools": tools,
                "stream": stream,
            }
        )
        data = llm_res.json()
        return data
    except:
        return {"error": "no data"}


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
    
    tools=[
        {
            "type": "function",
            "function" : {
                "name" : "book_search",
                "description" :
                    "Searches the bookstore database for book titles and authors using semantic search on 'query'. Returns a list of books in no particular order. Choose only the most applicable ones. Request more than one for similarity searches so it doesn't return a the original book. ",
                "parmeters" : {
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
