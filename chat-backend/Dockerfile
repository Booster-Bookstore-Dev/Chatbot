# Base stage with torch
FROM python:3.12-slim AS torch-base

WORKDIR /

RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install sentence-transformers --no-deps
RUN pip install transformers scikit-learn



# Stage 1: build FAISS index
FROM torch-base AS faiss-builder

COPY /faiss/requirements.txt .
RUN pip install -r requirements.txt

COPY /faiss/ .
RUN python build_index.py


# Stage 2: app runtime
FROM torch-base AS app

WORKDIR /

COPY /app/requirements.txt /app/
RUN pip install -r ./app/requirements.txt

COPY --from=FAISS-builder /data/ ./data/
COPY /app .

CMD ["python", "app.py"]
