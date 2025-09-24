FROM python:3.8-slim-bullseye

RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libnacl-dev \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "-u", "bot.py"]