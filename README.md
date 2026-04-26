# Minimal SIEM Pipeline

Docker-based lab for detecting repeated failed logins with a small SIEM-style pipeline:

```text
Flask app -> Fluent Bit -> Elasticsearch -> Kibana
```

The Flask app writes JSON login events to `/logs/app.log`. Fluent Bit tails the file and sends events to Elasticsearch index `siem-app-logs`. Kibana is used to view logs and run an alert rule for brute-force-like behavior: more than 5 failed logins in 1 minute.

## Run

```bash
docker compose up -d --build
./demo/setup_kibana.sh
./demo/trigger_failed_logins.sh
```

Then open:

```text
http://localhost:5601
```

Expected result: Kibana has a `siem-app-logs` data view and a `Failed login burst` alert rule. After the demo script sends failed logins, the rule fires and the alert is visible in Kibana.

## Telegram Notifications

Create a local `.env` file:

```bash
cp .env.example .env
```

Fill in `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, then run the watcher in a second terminal before triggering failed logins:

```bash
./demo/watch_telegram_alerts.sh
```

When the Kibana rule becomes active, the watcher sends a Telegram message.

## Useful URLs

```text
Flask app:      http://localhost:5000
Elasticsearch: http://localhost:9200
Kibana:        http://localhost:5601
```

Valid demo login:

```text
username: admin
password: password123
```

## Quick Checks

```bash
docker compose ps
curl http://localhost:5000
curl http://localhost:9200
curl "http://localhost:9200/siem-app-logs/_count?pretty"
```

More implementation details, screenshots, limitations, and notification setup notes are in [docs/report.md](/home/egrapa/prog/ssd-SIEM/docs/report.md).
