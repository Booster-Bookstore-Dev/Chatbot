# Booster Bookstore Customer Support Chatbot

This project is a locally hosted AI-powered customer support chatbot designed to improve the online shopping experience at Booster Bookstore. The chatbot helps customers quickly find books, navigate the website, and access answers to frequently asked questions, reducing frustration and boosting satisfaction and sales.

## Features

-   Semantic search across a MongoDB book database using FAISS vector indexing
-   Conversational AI powered by Ollama LLM (Mistral 7B) for FAQs, navigation, and book recommendations
-   Fully containerized with Docker Compose for easy deployment
-   REST API backend with Flask connecting to Ollama for intelligent responses
-   User-friendly frontend with Nginx reverse proxy for accessibility across devices
-   CSV upload interface with drag-and-drop support for bulk book management
-   Secure data handling with MongoDB authentication
-   Modular design (frontend, chat-backend, db-backend, database) for scalability and maintainability
-   Optional Cloudflare Tunnel deployment for secure remote access

## Project Goals

-   Average response time under 10 seconds
-   90% accuracy for FAQ responses
-   85%+ user satisfaction
-   90%+ client satisfaction

This project represents a customizable, privacy-conscious alternative to cloud-based chat solutions, enabling Booster Bookstore to better serve customers and compete in the online marketplace.

## Architecture

The system consists of five main services orchestrated by Docker Compose:

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ HTTP (localhost:3000 or via Cloudflare)
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                      Frontend (Nginx)                           │
│  - Serves static HTML/CSS/JS                                    │
│  - Proxies /api/* → chat-backend:5050                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Internal Network
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                   Chat-Backend (Flask)                          │
│  - Handles /chat and /search endpoints                          │
│  - FAISS semantic search with SentenceTransformer               │
│  - Calls Ollama LLM on host via host.docker.internal            │
│  - Fetches book data from db-backend                            │
└────────┬─────────────────────────────────────────┬──────────────┘
         │                                         │
         │ Fetch Books                             │ LLM Requests
         │                                         │
┌────────▼─────────────────────┐     ┌─────────────▼──────────────┐
│  DB-Backend (Flask)          │     │  Ollama (Host Machine)     │
│  - /books API                │     │  - mistral:7b model        │
│  - /upload_books             │     │  - Runs on :11434          │
│  - /manage page              │     └────────────────────────────┘
│  - /rebuild_index trigger    │
└────────┬─────────────────────┘
         │
         │ MongoDB Connection
         │
┌────────▼─────────────────────┐
│  MongoDB                     │
│  - books collection          │
│  - Persistent storage        │
└──────────────────────────────┘

Optional:
┌──────────────────────────────┐
│  Mongo Express (Web UI)      │
│  - Database admin at         │
│         :8081/mongo          │
└──────────────────────────────┘

┌──────────────────────────────┐
│  Cloudflared Tunnel          │
│  - Secure remote access      │
└──────────────────────────────┘
```

## Technology Stack

-   **Frontend**: HTML, CSS, JavaScript served via Nginx
-   **Backend**: Flask (Python) with MongoDB, FAISS, and SentenceTransformer
-   **Database**: MongoDB with Mongo Express admin interface
-   **LLM**: Ollama (Mistral 7B model)
-   **Containerization**: Docker and Docker Compose
-   **Deployment**: Cloudflare Tunnel (optional)

## Prerequisites

Before deploying this project, ensure you have the following installed:

1. **Docker and Docker Compose** (latest version)
2. **Ollama Application** running as a server on your host machine
3. **Mistral 7B model** downloaded in Ollama
4. **Git** for cloning the repository

### Installing Ollama and Mistral

1. Download and install Ollama from https://ollama.ai
2. Start Ollama as a server (it should run in the background)
3. Download the Mistral 7B model:

```
ollama pull mistral:7b
```

4. Verify the model is available:

```
ollama list
```

The Ollama server must be running on the host machine at http://localhost:11434 for the chat-backend to access it via host.docker.internal.

## Environment Variables

Create a .env file in the project root with the following variables:

```
OLLAMA_MODEL=mistral:7b
INDEX_PATH=./data
INDEX_NAME=faiss.index
DATAFRAME_NAME=books.parquet
DATA_PATH=./start_data
MONGO_DATA=/path/to/your/mongo-data/
MONGO_INITDB_ROOT_USERNAME=root
MONGO_INITDB_ROOT_PASSWORD=your_secure_password
MONGO_INITDB_DATABASE=mydb
```

Important notes:

-   MONGO_DATA should point to a directory on your host for persistent database storage
-   MONGO_INITDB_ROOT_PASSWORD should be changed from the default for production use
-   CLOUDFLARE_TOKEN is only needed if deploying with Cloudflare Tunnel

## Deployment

### Local Development

To run the application in development mode:

1. Ensure Ollama is running on your host machine
2. Navigate to the project root directory
3. Run the development script:

```
./scripts/dev.sh
```

This will start all services with live reloading enabled. Access the application at:

-   Frontend: http://localhost:3000
-   Chat Backend API: http://localhost:5050
-   DB Backend API: http://localhost:6060
-   MongoDB: http://localhost:27017
-   Mongo Express: http://localhost:8081

### Production Deployment

To deploy the application for production use:

1. Ensure Ollama is running on your host machine
2. Verify your .env file contains production-ready credentials
3. Navigate to the project root directory
4. Run the deployment script:

```
./scripts/deploy.sh
```

This will build all containers and start the services in detached mode.

### Cloudflare Tunnel Setup (Optional)

To enable secure remote access via Cloudflare Tunnel:

1. Log in to the Cloudflare dashboard at https://dash.cloudflare.com

2. Navigate to Zero Trust > Networks > Tunnels

3. Click "Create a tunnel"

4. Select "Cloudflared" as the connector type

5. Give your tunnel a name (e.g., "booster-bookstore") and click "Save tunnel"

6. Cloudflare will display a token - copy this token value

7. Add the token to your .env file:

```
CLOUDFLARE_TOKEN=your_tunnel_token_here
```

8. Click "Next" and configure your public hostnames:

    - Public hostname: books.yourdomain.com (or your desired subdomain)
        - Service: HTTP
        - URL: frontend:80
    - Public hostname: admin.yourdomain.com
        - Path: /mongo
        - Service: HTTP
        - URL: mongo-express:8081
    - Public hostname: admin.yourdomain.com
        - Path: /manage
        - Service: HTTP
        - URL: db-backend:6060

9. Click "Save tunnel"

10. The tunnel service is already configured in docker-compose.yaml and will be deployed automatically when you run:

```
./scripts/deploy.sh
```

Your application will now be accessible at:

-   Main site: https://books.yourdomain.com
-   Database admin: https://admin.yourdomain.com/mongo
-   Book management: https://admin.yourdomain.com/manage

## Managing Books via the /manage Interface

The /manage page provides a web interface for bulk book management.

### Accessing the Management Interface

Navigate to http://localhost:6060/manage (or your deployed domain).

### Preparing CSV Files

Your CSV file must include headers matching the expected book fields:

```
title,authors,genres,isbn,release_date,std_price,sale_price,stock_count
```

Example data:

```
title,authors,genres,isbn,release_date,std_price,sale_price,stock_count
Dune,Frank Herbert,Science Fiction,9780441172719,1965-08-01,9.99,7.99,15
The Hobbit,J.R.R. Tolkien,Fantasy,9780547928227,1937-09-21,8.49,6.99,30
```

### Uploading Books

1. Drag and drop your CSV file into the upload zone or click to browse
2. Select upload mode:
    - Append: Adds books to the existing database (default)
    - Replace: Deletes all existing books and replaces with CSV data
3. Click Upload CSV
4. Wait for confirmation message

Warning: Replace mode permanently deletes all existing records.

### Rebuilding the Search Index

After uploading new book data, click Rebuild Index to update the FAISS search index. This triggers the chat-backend to:

1. Fetch all books from MongoDB
2. Generate new embeddings using SentenceTransformer
3. Rebuild the FAISS index for semantic search
4. Save the index for future queries

## API Endpoints

### Chat Backend (Port 5050)

**POST /chat**

-   Accepts user messages and conversation history
-   Returns LLM response with optional tool calls
-   Request body:

```
  {
    "message": "Find me books about space exploration",
    "history": [] // optional conversation history
  }
```

**POST /search**

-   Direct FAISS semantic search (for testing)
-   Request body:

```
  {
    "query": "science fiction",
    "k": 5
  }
```

**POST /rebuild_index**

-   Triggers index rebuild from current MongoDB data
-   No request body required

### DB Backend (Port 6060)

**GET /books**

-   Returns all books in JSON format

**POST /books**

-   Adds a single book to the database
-   Request body:

```
  {
    "title": "Book Title",
    "authors": "Author Name",
    "genres": "Genre",
    "isbn": "1234567890",
    "release_date": "2024-01-01",
    "std_price": "19.99",
    "sale_price": "14.99",
    "stock_count": "25"
  }
```

**GET /manage**

-   Serves the web-based CSV upload interface

**POST /upload_books**

-   Bulk upload books via CSV
-   Form data:
    -   file: CSV file
    -   mode: "append" or "replace"

**POST /rebuild_index**

-   Proxy endpoint that triggers chat-backend index rebuild

## How It Works

### Semantic Search with FAISS

The chat-backend uses FAISS (Facebook AI Similarity Search) for efficient semantic search:

1. Books are combined into text strings: "title by author"
2. SentenceTransformer (all-MiniLM-L6-v2) generates 384-dimensional embeddings
3. Embeddings are indexed in FAISS using L2 distance
4. User queries are encoded and searched against the index
5. Top k similar books are returned based on semantic similarity

### LLM Integration

The chatbot uses Ollama with the Mistral 7B model for natural language understanding:

1. User messages are sent to the chat-backend
2. The system prompt defines assistant behavior and available tools
3. The LLM can call two tools:
    - book_search: Performs semantic search using FAISS
    - reply: Sends responses back to the user
4. Tool results are appended to the conversation and the LLM generates a final response
5. The complete conversation history is returned for context preservation

### Data Flow

1. User submits query via frontend
2. Frontend proxies request to chat-backend via /api
3. Chat-backend processes query through Ollama
4. If book search is needed, FAISS index is queried
5. Book data is fetched from MongoDB via db-backend
6. LLM generates response using search results
7. Response is returned to user via frontend

## Troubleshooting

### "Database not connected" Error

-   Verify MongoDB service is running: `docker ps`
-   Check MONGO_URI in .env file
-   Ensure MongoDB container has started before db-backend
-   Check MongoDB logs: `docker logs mongo`

### "Error contacting LLM" Message

-   Verify Ollama is running on host: `ollama list`
-   Test Ollama API: `curl http://localhost:11434/api/tags`
-   Ensure Mistral 7B model is downloaded: `ollama pull mistral:7b`
-   Check chat-backend can reach host: `docker exec chat-backend curl http://host.docker.internal:11434/api/tags`

### Search Returns No Results

-   Verify books exist in MongoDB: visit http://localhost:8081
-   Check if FAISS index exists: `docker exec chat-backend ls /data`
-   Rebuild index: POST to http://localhost:5050/rebuild_index
-   Check chat-backend logs: `docker logs chat-backend`

### CSV Upload Fails

-   Verify CSV has required headers
-   Check file encoding (must be UTF-8)
-   Ensure MongoDB has sufficient storage space
-   Review db-backend logs: `docker logs db-backend`

### Cloudflare Tunnel Not Working

-   Verify tunnel credentials file exists in ./cloudflared/
-   Check tunnel status in Cloudflare dashboard
-   Ensure DNS is configured correctly
-   Review cloudflared logs: `docker logs cloudflared`

### Port Already in Use

-   Check for conflicting services: `lsof -i :3000` (or relevant port)
-   Stop conflicting services or change port in docker-compose.yaml
-   Restart Docker containers after changes

## Maintenance and Development

### Viewing Logs

View logs for all services:

```
docker compose logs -f
```

View logs for a specific service:

```
docker logs -f chat-backend
```

### Stopping Services

```
docker compose down
```

To remove volumes and reset database:

```
docker compose down -v
```

### Updating the Model

To switch to a different Ollama model:

1. Pull the new model: `ollama pull <model-name>`
2. Update OLLAMA_MODEL in .env
3. Restart services: `docker compose restart chat-backend`

### Database Backup

To backup MongoDB data:

```
docker exec mongo mongodump --out=/dump --username=root --password=your_password
docker cp mongo:/dump ./backup
```

To restore from backup:

```
docker cp ./backup mongo:/dump
docker exec mongo mongorestore /dump --username=root --password=your_password
```

### Scaling Considerations

For production environments with high traffic:

-   Add load balancing for frontend and backend services
-   Increase MongoDB replica set for redundancy
-   Implement caching layer (Redis) for frequent queries
-   Monitor resource usage and adjust container limits
-   Set up logging aggregation and monitoring

## Project Structure

```
booster-bookstore/
├── chat-backend/
│   ├── app.py                 # Flask API with FAISS and LLM integration
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Chat backend container config
│   └── data/                 # FAISS index storage (volume-mounted)
├── db-backend/
│   ├── app.py                # Flask API for MongoDB operations
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile           # DB backend container config
│   └── templates/
│       └── manage.html      # CSV upload interface
├── frontend/
│   ├── index.html           # Main chat interface
│   ├── script.js            # Frontend logic
│   ├── style.css            # Styling
│   ├── nginx.conf           # Nginx reverse proxy config
│   └── Dockerfile           # Frontend container config
├── scripts/
│   ├── deploy.sh            # Production deployment script
│   └── dev.sh               # Development environment script
├── docker-compose.yaml      # Service orchestration
├── .env                     # Environment variables
└── README.md               # This file
```

## License

This project is developed for academic purposes as part of a customer support system implementation.

## Support

For issues, questions, or contributions, please contact the project maintainer or submit an issue to the project repository.
