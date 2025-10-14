FROM python:3.12-slim

WORKDIR /

RUN pip install flask
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install sentence-transformers 

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

COPY {BOOKS_DATA_PATH} /data/books_data.csv

CMD ["python", "app.py"]
