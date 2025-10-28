FROM python:3.12-slim

WORKDIR /app

# Copy everything into the container
COPY . /app

RUN pip install -r requirements.txt

CMD ["python", "app.py"]
