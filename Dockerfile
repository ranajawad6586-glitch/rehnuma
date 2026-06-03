FROM python:3.11-slim

# System deps:
#  - curl for the compose healthcheck
#  - the lib* / fonts packages are WeasyPrint's runtime dependencies (Pango/Cairo/HarfBuzz)
#    used to render the tenancy agreement PDF server-side (M8).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
        libharfbuzz-subset0 libgdk-pixbuf-2.0-0 libcairo2 libffi8 \
        shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Honor $PORT (Render/Heroku set it); default 8000 for local compose.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
