FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
# Pick up Debian security fixes that the base image has not shipped yet.
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
# pip, setuptools and wheel are not needed at runtime; removing them also removes the
# vulnerable copies bundled inside pip.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip setuptools wheel

COPY src ./src

RUN useradd --system --uid 10001 appuser
USER appuser

EXPOSE 8000

CMD ["python", "src/main.py"]
