FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1) Dependencies, in their own layer: Docker reuses it until a requirements file changes.
COPY requirements.txt requirements-prod.txt ./
RUN pip install -r requirements-prod.txt

# 2) The application code: changes often, and copying it takes seconds.
COPY . .

# Gather every app's static files (ours, the admin's, DRF's) for WhiteNoise.
# Settings need a secret key to load; this throwaway one is only used here.
RUN DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput

# Don't run as root inside the container.
RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/', timeout=2)"]

# Apply pending migrations, then start Gunicorn (settings in gunicorn.conf.py).
# exec makes Gunicorn the main process, so it receives Docker's stop signal.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi"]
