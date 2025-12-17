FROM python:3.11-slim

WORKDIR /app

RUN pip install boto3

COPY process.py .

RUN chmod +x process.py

CMD ["python", "process.py"]
