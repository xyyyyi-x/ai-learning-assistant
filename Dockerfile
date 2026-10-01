FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TASK_DB_PATH=/data/tasks.db

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY frontend/ ./frontend/
COPY knowledge/ ./knowledge/

RUN mkdir -p /data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api_app:app", "--host", "0.0.0.0", "--port", "8000"]