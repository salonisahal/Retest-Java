#!/bin/sh
set -e
# Wait for the database, apply migrations, seed demo data (idempotent), then serve.
for i in $(seq 1 30); do
  if alembic upgrade head; then break; fi
  echo "database not ready, retrying ($i/30)..."; sleep 2
done
python -m app.seed.seed_data
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
