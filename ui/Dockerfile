FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY ui/requirements.txt /app/ui/requirements.txt
RUN pip install --no-cache-dir -r /app/ui/requirements.txt

COPY ui /app/ui

EXPOSE 8501

CMD ["streamlit", "run", "/app/ui/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]