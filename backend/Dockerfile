# Backend image for Railway (or any container host). Targets 3.12 rather
# than the 3.13 used locally for a wider compatibility margin on a fresh
# build — nothing here needs 3.13 specifically.
FROM python:3.12-slim

WORKDIR /app

# System deps for building any packages that need compilation (some
# LangChain transitive deps ship no prebuilt wheel for every platform).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway (and most container hosts) inject PORT at runtime — the app must
# bind to it, not to a value baked in at build time.
ENV PORT=8000
EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
