FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
# Pick up Debian security fixes that the base image has not shipped yet.
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
# pip, setuptools and wheel are not needed at runtime; removing them also removes the
# vulnerable copies bundled inside pip.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip setuptools wheel

COPY src/ ./src/

EXPOSE 8080

RUN useradd --system --uid 10001 --no-create-home appuser
USER appuser

CMD ["python", "src/main.py"]
