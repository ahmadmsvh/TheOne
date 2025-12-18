FROM python:3.11-slim

WORKDIR /app

COPY notification-service/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY shared /app/shared
RUN pip install --no-cache-dir -e /app/shared

COPY notification-service .


EXPOSE 5002

CMD ["python", "main.py"]

