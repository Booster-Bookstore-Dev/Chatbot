FROM python:3.14-rc-alpine as FAISS-builder

WORKDIR /

COPY /faiss/requirements.txt .

RUN pip install -r requirements.txt

