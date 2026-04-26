#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"
RULE_NAME="${RULE_NAME:-Failed login burst}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-10}"
TELEGRAM_API_URL="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN:-}/sendMessage"

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  echo "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in the environment or .env file." >&2
  exit 1
fi

echo "Waiting for Kibana at ${KIBANA_URL}"
until curl -fsS "${KIBANA_URL}/api/status" >/dev/null; do
  sleep 5
done

encoded_rule_name="$(RULE_NAME="${RULE_NAME}" python3 - <<'PY'
import os
import urllib.parse

print(urllib.parse.quote(os.environ["RULE_NAME"]))
PY
)"

rule_id="$(
  curl -fsS "${KIBANA_URL}/api/alerting/rules/_find?search=${encoded_rule_name}&per_page=100" \
    -H "kbn-xsrf: true" |
  RULE_NAME="${RULE_NAME}" python3 -c 'import json,os,sys; data=json.load(sys.stdin); name=os.environ["RULE_NAME"]; print(next((r["id"] for r in data.get("data", []) if r.get("name") == name), ""))'
)"

if [[ -z "${rule_id}" ]]; then
  echo "Kibana rule '${RULE_NAME}' was not found. Run ./demo/setup_kibana.sh first." >&2
  exit 1
fi

send_telegram_message() {
  local text="$1"

  curl -fsS -X POST "${TELEGRAM_API_URL}" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${text}" \
    -d "disable_web_page_preview=true" \
    >/dev/null
}

last_notified_execution=""

echo "Watching Kibana rule '${RULE_NAME}' for active alerts. Press Ctrl+C to stop."

while true; do
  rule_json="$(curl -fsS "${KIBANA_URL}/api/alerting/rule/${rule_id}" -H "kbn-xsrf: true")"

  parsed="$(
    printf '%s' "${rule_json}" |
    python3 -c '
import json
import sys

rule = json.load(sys.stdin)
last_run = rule.get("last_run") or {}
counts = last_run.get("alerts_count") or {}
print(rule.get("execution_status", {}).get("status", "unknown"))
print(counts.get("active", 0))
print(counts.get("new", 0))
print(rule.get("execution_status", {}).get("last_execution_date", "unknown"))
'
  )"

  status="$(printf '%s\n' "${parsed}" | sed -n '1p')"
  active_count="$(printf '%s\n' "${parsed}" | sed -n '2p')"
  new_count="$(printf '%s\n' "${parsed}" | sed -n '3p')"
  last_execution_date="$(printf '%s\n' "${parsed}" | sed -n '4p')"

  if [[ "${status}" == "active" && "${active_count}" -gt 0 && "${last_execution_date}" != "${last_notified_execution}" ]]; then
    message="SIEM alert fired: ${RULE_NAME}

Condition: more than 5 failed login attempts in 1 minute
Active alerts: ${active_count}
New alerts: ${new_count}
Execution time: ${last_execution_date}
Kibana: ${KIBANA_URL}"

    send_telegram_message "${message}"
    echo "Telegram notification sent for execution ${last_execution_date}"
    last_notified_execution="${last_execution_date}"
  fi

  sleep "${POLL_INTERVAL_SECONDS}"
done
