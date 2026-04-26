#!/usr/bin/env bash
set -euo pipefail

TARGET_URL="${TARGET_URL:-http://localhost:5000/login}"

echo "Sending 6 failed login attempts to ${TARGET_URL}"

for i in {1..6}; do
  echo "Attempt ${i}/6: username=admin password=wrong"
  status_code="$(
    curl -sS -o /dev/null -w "%{http_code}" \
      -X POST "${TARGET_URL}" \
      -d "username=admin" \
      -d "password=wrong"
  )"
  echo "HTTP ${status_code}"
  sleep 0.5
done

echo "Finished. Check Kibana Discover and the configured alert rule status."
