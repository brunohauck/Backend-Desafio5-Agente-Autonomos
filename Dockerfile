# path: Dockerfile
FROM python:3.11-slim

# Evita criação de .pyc e garante logs diretos
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
ENV PYTHONPATH=/app PORT=10000

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o backend completo
COPY . .

# Cria diretórios necessários
RUN mkdir -p storage/datasets storage/profiles storage/uploads storage/plots

EXPOSE 10000

# Inicia o FastAPI diretamente (sem start.sh)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]