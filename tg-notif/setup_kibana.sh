#!/usr/bin/env bash
set -euo pipefail

KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"
RULE_NAME="${RULE_NAME:-Failed login burst}"

echo "Waiting for Kibana at ${KIBANA_URL}"
until curl -fsS "${KIBANA_URL}/api/status" >/dev/null; do
  sleep 5
done

echo "Creating or refreshing Kibana data view: siem-app-logs"
curl -fsS -X POST "${KIBANA_URL}/api/data_views/data_view" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{"data_view":{"title":"siem-app-logs","name":"siem-app-logs","timeFieldName":"@timestamp"}}' \
  >/tmp/siem-data-view-response.json || true

echo "Creating alert rule: ${RULE_NAME}"
rule_payload="$(
  python3 - <<'PY'
import json

print(json.dumps({
    "name": "Failed login burst",
    "tags": ["siem", "bruteforce-demo"],
    "rule_type_id": ".index-threshold",
    "consumer": "stackAlerts",
    "schedule": {"interval": "1m"},
    "params": {
        "index": ["siem-app-logs"],
        "timeField": "@timestamp",
        "aggType": "count",
        "groupBy": "all",
        "thresholdComparator": ">",
        "threshold": [5],
        "timeWindowSize": 1,
        "timeWindowUnit": "m",
        "filterKuery": 'event_type: "login_attempt" and status: "failed"',
    },
    "actions": [],
    "notify_when": "onActionGroupChange",
}))
PY
)"

existing_rule_id="$(
  curl -fsS "${KIBANA_URL}/api/alerting/rules/_find?search=Failed%20login%20burst&per_page=100" \
    -H "kbn-xsrf: true" |
  python3 -c 'import json,sys; data=json.load(sys.stdin); print(next((r["id"] for r in data.get("data", []) if r.get("name") == "Failed login burst"), ""))'
)"

if [[ -n "${existing_rule_id}" ]]; then
  echo "Rule already exists: ${existing_rule_id}"
else
  curl -fsS -X POST "${KIBANA_URL}/api/alerting/rule" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -d "${rule_payload}" \
    >/tmp/siem-alert-rule-response.json
  echo "Rule created. Response saved to /tmp/siem-alert-rule-response.json"
fi

echo "Kibana setup complete."
