import json
import os
import threading
from datetime import datetime, timezone

from flask import Flask, Response, request


app = Flask(__name__)

LOG_FILE = os.environ.get("LOG_FILE", "/logs/app.log")
VALID_USERNAME = "admin"
VALID_PASSWORD = "password123"
_log_lock = threading.Lock()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_log_file() -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    open(LOG_FILE, "a", encoding="utf-8").close()


def client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.remote_addr or "unknown"


def write_login_log(username: str, status: str) -> None:
    event = {
        "timestamp": utc_timestamp(),
        "event_type": "login_attempt",
        "username": username,
        "status": status,
        "client_ip": client_ip(),
        "path": request.path,
        "method": request.method,
        "user_agent": request.headers.get("User-Agent", ""),
        "message": "Successful login" if status == "success" else "Failed login attempt",
    }

    with _log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(event, separators=(",", ":")) + "\n")


@app.get("/")
def index() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Minimal SIEM Demo Login</title>
    <style>
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        font-family: Georgia, 'Times New Roman', serif;
        background: radial-gradient(circle at top left, #f4d35e, transparent 30%),
          linear-gradient(135deg, #0b132b, #1c2541 55%, #3a506b);
        color: #f7fff7;
      }
      main {
        width: min(92vw, 420px);
        padding: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 24px;
        background: rgba(11, 19, 43, 0.76);
        box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
      }
      label, input, button { display: block; width: 100%; box-sizing: border-box; }
      label { margin: 1rem 0 0.35rem; color: #d8e2dc; }
      input {
        padding: 0.8rem;
        border-radius: 12px;
        border: 1px solid #748cab;
        background: #f7fff7;
      }
      button {
        margin-top: 1.2rem;
        padding: 0.85rem;
        border: 0;
        border-radius: 999px;
        background: #f4d35e;
        color: #0b132b;
        font-weight: 700;
        cursor: pointer;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Minimal SIEM Demo</h1>
      <p>Submit login attempts here. Each attempt is written as JSON to <code>/logs/app.log</code>.</p>
      <form method="post" action="/login">
        <label for="username">Username</label>
        <input id="username" name="username" value="admin" autocomplete="username">
        <label for="password">Password</label>
        <input id="password" name="password" type="password" autocomplete="current-password">
        <button type="submit">Log in</button>
      </form>
    </main>
  </body>
</html>
"""


@app.post("/login")
def login() -> tuple[Response, int]:
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if username == VALID_USERNAME and password == VALID_PASSWORD:
        write_login_log(username, "success")
        return Response("Login successful\n", mimetype="text/plain"), 200

    write_login_log(username, "failed")
    return Response("Login failed\n", mimetype="text/plain"), 401


if __name__ == "__main__":
    ensure_log_file()
    app.run(host="0.0.0.0", port=5000)
