FROM python:3.11-slim

WORKDIR /app

COPY auth-service /app/auth-service

RUN pip install --no-cache-dir -r auth-service/requirements.txt

COPY shared /app/shared
RUN pip install --no-cache-dir -e /app/shared

WORKDIR /app/auth-service

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

