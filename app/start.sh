# path: start.sh
#!/usr/bin/env sh
set -e

PORT="${PORT:-10000}"

echo "🚀 Starting backend on port $PORT"
# Garante que as pastas existem para salvar arquivos/plots
mkdir -p api/storage/datasets api/storage/profiles api/storage/uploads api/storage/plots

# Sobe FastAPI
exec uvicorn api.main:app --host 0.0.0.0 --port "$PORT"