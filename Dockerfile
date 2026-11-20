FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home appuser \
 && chown -R appuser /app
USER appuser

EXPOSE 8080
CMD ["python", "main.py"]
