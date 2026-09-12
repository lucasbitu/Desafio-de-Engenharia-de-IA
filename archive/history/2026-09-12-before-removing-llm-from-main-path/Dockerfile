FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TICKET_CLASSIFIER_PROJECT_ROOT=/app

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip \
    && python -m pip install ".[delivery]"

COPY data_split/outputs/train.csv data_split/outputs/train.csv
COPY data_split/outputs/validation.csv data_split/outputs/validation.csv
COPY data_split/outputs/split_metadata.json data_split/outputs/split_metadata.json
COPY app.py ./app.py

RUN ticket-train

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)"

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
