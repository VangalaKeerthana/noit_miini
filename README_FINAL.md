# Final stack: strict CORS + tuned NGINX

## Files
- api/server.py              # FastAPI with strict CORS (FRONTEND_ORIGIN env)
- utils/auth.py, utils/db.py # auth + DB helpers
- web/index.html             # tiny static UI
- nginx/default.conf         # gzip + cache headers (no-cache for HTML)
- Dockerfile.api / Dockerfile.web
- docker-compose.yml
- requirements-docker.txt

## .env
Put this at repo root:
```ini
OPENAI_API_KEY=sk-...
SECRET_KEY=some-long-random-string
FRONTEND_ORIGIN=http://localhost:8080
```

## Run (Docker)
```bash
docker compose build
docker compose up -d
# API: http://localhost:8000/docs
# WEB: http://localhost:8080
```

## Run (dev, no Docker)
```bash
pip install -r requirements-docker.txt   # or your main requirements
python -c "from utils.db import init_db; init_db(); print('DB ready')"
uvicorn api.server:app --reload
# open web/index.html in your browser
```
