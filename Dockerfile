# path: Dockerfile
FROM python:3.11-slim

# Configurações básicas de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Diretório de trabalho
WORKDIR /app

# Torna "api" importável e define porta padrão
ENV PYTHONPATH=/app \
    PORT=10000

# Dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código do app
COPY . .

# Script de start
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 10000

# Inicia o backend
ENTRYPOINT ["/app/start.sh"]