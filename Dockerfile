FROM python:3.12-slim

WORKDIR /app

# Hindari buffering log python
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV HOST=0.0.0.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Inisialisasi basis data SQLite lokal agar selalu siap digunakan dalam kontainer
RUN python data/database/init_db.py

EXPOSE 8000

CMD ["python", "run_web.py"]
