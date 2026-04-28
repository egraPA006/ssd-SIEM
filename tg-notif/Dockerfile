FROM python:3.12-slim-trixie

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY setup_kibana.sh .
COPY app.py .

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

CMD bash setup_kibana.sh && python app.py
