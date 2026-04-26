# Architecture Diagram

```mermaid
flowchart LR
    A[Flask Web App<br/>localhost:5000] -->|writes JSON lines| L[(Shared volume<br/>/logs/app.log)]
    L -->|tail + parse JSON| F[Fluent Bit]
    F -->|Elasticsearch output| E[(Elasticsearch<br/>siem-app-logs<br/>localhost:9200)]
    E -->|data view + rules| K[Kibana<br/>localhost:5601]
    K -->|built-in alert status| I[(Kibana alert document)]
    K -. polled by .-> W[Telegram watcher script]
    W -->|sendMessage API| T[Telegram chat]
```

The demo uses a shared Docker volume for the application log file. Fluent Bit tails that file, parses each JSON line, and sends the resulting events to Elasticsearch. Kibana evaluates the failed-login threshold rule. The optional Telegram watcher reads the Kibana rule status and sends a Telegram message when the rule becomes active.
