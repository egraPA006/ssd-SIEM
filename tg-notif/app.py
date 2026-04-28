import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def load_env(path=".env"):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip("\"'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except FileNotFoundError:
        pass


def wait_for_kibana(url, interval=5):
    print(f"Waiting for Kibana at {url}")
    while True:
        try:
            urllib.request.urlopen(f"{url}/api/status", timeout=5)
            return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            time.sleep(interval)


def _kibana_get(url):
    req = urllib.request.Request(url, headers={"kbn-xsrf": "true"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(
            f"Kibana request failed ({e.code}): {detail}"
        ) from e


def find_rule_id(kibana_url, rule_name):
    encoded = urllib.parse.quote(rule_name)
    data = _kibana_get(
        f"{kibana_url}/api/alerting/rules/_find?search={encoded}&per_page=100"
    )
    for rule in data.get("data", []):
        if rule.get("name") == rule_name:
            return rule["id"]
    print(
        f"Kibana rule '{rule_name}' was not found. Run setup_kibana.py first.",
        file=sys.stderr,
    )
    sys.exit(1)


def fetch_rule(kibana_url, rule_id):
    return _kibana_get(f"{kibana_url}/api/alerting/rule/{rule_id}")


def parse_rule_status(rule):
    exec_status = rule.get("execution_status") or {}
    counts = (rule.get("last_run") or {}).get("alerts_count") or {}
    return {
        "status": exec_status.get("status", "unknown"),
        "active_count": counts.get("active", 0),
        "new_count": counts.get("new", 0),
        "last_execution_date": exec_status.get(
            "last_execution_date", "unknown"
        ),
    }


def send_telegram(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Telegram send failed ({e.code}): {detail}") from e


def watch_loop(kibana_url, rule_id, rule_name, bot_token, chat_id, interval):
    print(
        f"Watching Kibana rule '{rule_name}' for active alerts. Press Ctrl+C to stop."
    )
    last_notified = ""
    while True:
        rule = fetch_rule(kibana_url, rule_id)
        s = parse_rule_status(rule)
        if (
            s["status"] == "active"
            and s["active_count"] > 0
            and s["last_execution_date"] != last_notified
        ):
            message = (
                f"SIEM alert fired: {rule_name}\n\n"
                f"Condition: more than 5 failed login attempts in 1 minute\n"
                f"Active alerts: {s['active_count']}\n"
                f"New alerts: {s['new_count']}\n"
                f"Execution time: {s['last_execution_date']}\n"
                f"Kibana: {kibana_url}"
            )
            send_telegram(bot_token, chat_id, message)
            print(
                f"Telegram notification sent for execution {s['last_execution_date']}"
            )
            last_notified = s["last_execution_date"]
        time.sleep(interval)


def main():
    load_env()

    kibana_url = os.environ.get("KIBANA_URL", "http://localhost:5601").rstrip(
        "/"
    )
    rule_name = os.environ.get("RULE_NAME", "Failed login burst")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    try:
        interval = int(os.environ.get("POLL_INTERVAL_SECONDS", "10"))
    except ValueError:
        print("POLL_INTERVAL_SECONDS must be an integer.", file=sys.stderr)
        sys.exit(1)

    if not bot_token or not chat_id:
        print(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in the environment or .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    wait_for_kibana(kibana_url)
    rule_id = find_rule_id(kibana_url, rule_name)

    try:
        watch_loop(
            kibana_url, rule_id, rule_name, bot_token, chat_id, interval
        )
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
