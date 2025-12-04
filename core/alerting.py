import asyncio
import smtplib
import time
from collections import defaultdict
from email.message import EmailMessage

import httpx


# Simple rate limiter per destination
class RateLimiter:
    def __init__(self, rate=1, per=60):
        self.rate = rate
        self.per = per
        self.allowance = defaultdict(lambda: rate)
        self.last_check = defaultdict(lambda: time.monotonic())

    async def acquire(self, key):
        now = time.monotonic()
        elapsed = now - self.last_check[key]
        self.last_check[key] = now
        self.allowance[key] += elapsed * (self.rate / self.per)
        if self.allowance[key] > self.rate:
            self.allowance[key] = self.rate
        if self.allowance[key] < 1.0:
            await asyncio.sleep((1.0 - self.allowance[key]) * (self.per / self.rate))
            self.allowance[key] = 0
        else:
            self.allowance[key] -= 1.0


rate_limiter = RateLimiter()


async def send_slack(webhook_url, message, level="INFO"):
    await rate_limiter.acquire(webhook_url)
    async with httpx.AsyncClient() as client:
        payload = {"text": f"[{level}] {message}"}
        r = await client.post(webhook_url, json=payload)
        return r.status_code


async def send_email(smtp_host, smtp_port, from_addr, to_addrs, subject, body, username=None, password=None):
    key = smtp_host
    await rate_limiter.acquire(key)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ",".join(to_addrs) if isinstance(to_addrs, (list, tuple)) else to_addrs
    msg.set_content(body)

    def _send():
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
            if username and password:
                s.starttls()
                s.login(username, password)
            s.send_message(msg)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _send)


async def notify(config: dict, level: str, title: str, body: str):
    # config: {'slack': {'webhook':..}, 'email': {...}}
    tasks = []
    if config.get("slack") and config["slack"].get("webhook"):
        tasks.append(send_slack(config["slack"]["webhook"], f"{title}\n{body}", level=level))
    if config.get("email") and config["email"].get("enabled"):
        e = config["email"]
        tasks.append(
            send_email(
                e.get("host"), e.get("port", 25), e.get("from"), e.get("to"), title, body, e.get("username"), e.get("password")
            )
        )
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


# Example payload generator
def slack_payload_example(title, summary):
    return {"text": f"*{title}*\n{summary}"}
