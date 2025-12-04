import asyncio
import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, rate, per):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            current = time.monotonic()
            time_passed = current - self.last_check
            self.last_check = current
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            if self.allowance < 1.0:
                await asyncio.sleep((1.0 - self.allowance) * (self.per / self.rate))
                self.allowance = 0
            else:
                self.allowance -= 1.0


class AsyncEngine:
    def __init__(self, max_concurrency=20, provider_limits=None):
        self.sem = asyncio.Semaphore(max_concurrency)
        self.provider_limiters = {}
        if provider_limits:
            for provider, (rate, per) in provider_limits.items():
                self.provider_limiters[provider] = RateLimiter(rate, per)

    async def run_task(self, coro, provider=None):
        async with self.sem:
            if provider and provider in self.provider_limiters:
                await self.provider_limiters[provider].acquire()
            return await coro
