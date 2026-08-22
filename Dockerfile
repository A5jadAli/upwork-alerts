FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
# token.json + seen.json live on a mounted volume so state survives restarts.
VOLUME ["/data"]
ENV TOKEN_FILE=/data/token.json SEEN_FILE=/data/seen.json
CMD ["python", "loop.py"]
