FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
EXPOSE 8080
RUN useradd --system --uid 10001 --no-create-home appuser
USER appuser

CMD ["python", "src/main.py"]
