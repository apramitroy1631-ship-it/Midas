# Railway build entrypoint — lives at the REPO ROOT deliberately.
#
# Railway's "Root Directory" per-service dashboard setting proved unreliable
# to configure (repeated builds kept analyzing the repo root regardless of
# what was set there), so rather than depend on that UI field taking effect,
# this Dockerfile sits where Railway looks by default — the repo root — and
# explicitly copies only from backend/. No dashboard setting required for
# the build to find the right thing to build.
#
# For local development, use backend/Dockerfile instead (build context =
# backend/ directly, matches how you'd run it from inside that folder). This
# root Dockerfile is Railway-specific — see railway.json alongside it.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Railway (and most container hosts) inject PORT at runtime.
ENV PORT=8000
EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
