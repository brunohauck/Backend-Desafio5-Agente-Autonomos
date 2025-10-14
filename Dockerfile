# path: Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
ENV PYTHONPATH=/app \
    PORT=10000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

EXPOSE 10000
ENTRYPOINT ["/app/start.sh"]