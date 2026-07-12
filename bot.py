"""
sudo-gateway/bot.py
Minimal always-on Discord gateway process for the Sudo Obfuscator bot.

Its only job is to hold a live gateway connection so the bot shows the green
"online" dot. Slash commands (/obf, /deobf) are served separately by the
Cloudflare interactions endpoint, so this process does not handle interactions.

A tiny HTTP health server binds $PORT so Render's web-service health check
passes, and a keep-alive thread pings it so the instance never spins down.
"""

import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen

import discord

TOKEN = os.environ.get("OBF_BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", "8080"))
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}")
STATUS_TEXT = os.environ.get("OBF_STATUS_TEXT", "Sudo Obfuscator")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sudo-gateway")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass


def run_health_server():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()


def keep_alive():
    import time
    while True:
        time.sleep(600)
        try:
            urlopen(f"{RENDER_URL}/health", timeout=10)
        except Exception:
            pass


intents = discord.Intents.default()
client = discord.Client(
    intents=intents,
    activity=discord.Game(name=STATUS_TEXT),
    status=discord.Status.online,
)


@client.event
async def on_ready():
    log.info("Gateway online as %s (id=%s)", client.user, client.user.id)


def main():
    if not TOKEN:
        raise SystemExit("OBF_BOT_TOKEN is not set")
    threading.Thread(target=run_health_server, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    log.info("Starting gateway (health on port %s)", PORT)
    client.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
