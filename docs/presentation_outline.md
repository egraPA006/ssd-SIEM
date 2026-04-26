# Presentation Outline

## 1. Problem - 1 min

Logs are produced everywhere, but without centralization and alerts they are hard to use. A failed login in one file may be easy to miss, especially when events are spread across applications and hosts.

## 2. Goal - 1 min

Build a minimal SIEM pipeline that collects application logs and detects repeated failed login attempts. The target detection is more than 5 failed logins within 1 minute.

## 3. Architecture - 2 min

Explain the flow:

```text
Flask App -> Fluent Bit -> Elasticsearch -> Kibana
```

The Flask app writes JSON logs to `/logs/app.log`. Fluent Bit tails the file, parses JSON, and sends records to Elasticsearch. Kibana reads from Elasticsearch for investigation and alerting.

## 4. Implementation - 2 min

Discuss Docker Compose and the four services: `app`, `fluent-bit`, `elasticsearch`, and `kibana`.

Show the JSON log schema and explain why structured logs are easier to search.

Show the Fluent Bit configuration: tail input, JSON parser, Elasticsearch output, and `siem-app-logs` target index.

Show the Kibana data view over `siem-app-logs`.

## 5. Demo Video - 1-2 min

Show the app running at `http://localhost:5000`.

Run:

```bash
./demo/trigger_failed_logins.sh
```

Show the failed login logs appearing in Kibana Discover.

Show the Kibana alert rule firing after the threshold is crossed.

## 6. Results and Limitations - 2 min

What works: the app produces JSON logs, Fluent Bit forwards them, Elasticsearch stores them, Kibana shows them, and the threshold rule detects repeated failed logins.

Limitations: the stack is local-only, Elastic security is disabled, the rule is threshold-based, there is no multi-service correlation, and Telegram notification needs bot credentials.

Production improvements: enable Elastic security, use native Kibana webhook notifications where licensing allows it, collect host and container logs, build dashboards, add more detections, and define an incident response workflow.
