import time
from collections import deque
import threading
class SlidingWindow:
    def __init__(self,limit:int,window:float):
        self.limit=limit
        self.window=window
        self.timestamps = deque()
        self.lock = threading.Lock()
    def allow(self,now):
        with self.lock:
            while self.timestamps and self.timestamps[0]<=now-self.window:
                self.timestamps.popleft()
            if len(self.timestamps)<self.limit:
                self.timestamps.append(now)
                remaining = self.limit - len(self.timestamps)
                return True,remaining,0
            else:
                retry_after = self.timestamps[0] + self.window - now
                return False,0,retry_after
class TokenBucket:
    def __init__(self,capacity,rate):
        self.capacity = capacity
        self.rate = rate
        self.tokens = capacity
        self.last = 0
        self.lock = threading.Lock()
    def allow(self,now,cost=1):
        with self.lock:
            time_passed = now - self.last
            new_tokens = time_passed * self.rate
            if self.tokens+new_tokens > self.capacity :
                self.tokens = self.capacity
            else:
                self.tokens += new_tokens
            self.last = now
            if self.tokens >= cost:
                self.tokens -=cost
                return True,self.tokens,0
            else:
                if cost>self.capacity:
                    return False,self.tokens,float('inf')
                retry_after = (cost-self.tokens)/self.rate
                return False,self.tokens,retry_after

class RateLimiter:
    def __init__(self, rules):
        self.strategies = {"SlidingWindow": SlidingWindow, "TokenBucket": TokenBucket}
        for resource, (strategy, config) in rules.items():
            if strategy not in self.strategies:
                raise ValueError(f"unknown strategy '{strategy}' for resource '{resource}'")
        self.rules = rules
        self.limiters = {}
        self.stats = {}
        self.lock = threading.Lock()
    def allow(self, client, resource, now):
        if resource not in self.rules:
            raise ValueError(f"unknown resource '{resource}'")
        key = (client, resource)
        with self.lock:
            if key not in self.limiters:
                strategy, config = self.rules[resource]
                self.limiters[key] = self.strategies[strategy](**config)
            if key not in self.stats:
                self.stats[key] = {"accepted": 0, "rejected": 0}
            bouncer = self.limiters[key]
        s = bouncer.allow(now)
        with self.lock:
            if s[0]:
                self.stats[key]["accepted"] += 1
            else:
                self.stats[key]["rejected"] += 1
        return s

    def get_stats(self, client, resource):
        with self.lock:
            key = (client, resource)
            if key not in self.stats:
                return {"accepted": 0, "rejected": 0}
            return dict(self.stats[key])


def check(name, got, expected):
    assert got == expected, f"FAIL {name}: got {got}, expected {expected}"
    print("ok:", name)


def test_isolation():
    rl = RateLimiter({"gpt": ("SlidingWindow", {"limit": 2, "window": 10}),
                      "embeddings": ("SlidingWindow", {"limit": 2, "window": 10})})
    check("alice t=0", rl.allow("alice", "gpt", 0), (True, 1, 0))
    check("alice t=1", rl.allow("alice", "gpt", 1), (True, 0, 0))
    check("alice t=2 rejected", rl.allow("alice", "gpt", 2), (False, 0, 8))
    check("bob unaffected", rl.allow("bob", "gpt", 2), (True, 1, 0))
    check("other resource unaffected", rl.allow("alice", "embeddings", 2), (True, 1, 0))


def test_expiry():
    rl = RateLimiter({"gpt": ("SlidingWindow", {"limit": 2, "window": 10})})
    rl.allow("alice", "gpt", 0)
    rl.allow("alice", "gpt", 1)
    rl.allow("alice", "gpt", 2)
    check("entry at t=0 expired at t=10", rl.allow("alice", "gpt", 10), (True, 0, 0))


def test_token_bucket():
    rl = RateLimiter({"gpt": ("TokenBucket", {"capacity": 2, "rate": 1})})
    check("tb call 1", rl.allow("alice", "gpt", 0), (True, 1, 0))
    check("tb call 2", rl.allow("alice", "gpt", 0), (True, 0, 0))
    check("tb call 3 rejected", rl.allow("alice", "gpt", 0), (False, 0, 1.0))
    check("tb refilled at t=1", rl.allow("alice", "gpt", 1), (True, 0, 0))


def test_stats():
    rl = RateLimiter({"gpt": ("SlidingWindow", {"limit": 2, "window": 10})})
    rl.allow("alice", "gpt", 0)
    rl.allow("alice", "gpt", 1)
    rl.allow("alice", "gpt", 2)
    check("alice stats", rl.get_stats("alice", "gpt"), {"accepted": 2, "rejected": 1})
    check("unknown client stats", rl.get_stats("nobody", "gpt"), {"accepted": 0, "rejected": 0})


def test_different_limits_per_resource():
    rl = RateLimiter({"gpt": ("SlidingWindow", {"limit": 1, "window": 10}),
                      "embeddings": ("SlidingWindow", {"limit": 3, "window": 10})})
    check("gpt call 1", rl.allow("alice", "gpt", 0), (True, 0, 0))
    check("gpt call 2 rejected", rl.allow("alice", "gpt", 1), (False, 0, 9))
    check("emb call 1", rl.allow("alice", "embeddings", 0), (True, 2, 0))
    check("emb call 2", rl.allow("alice", "embeddings", 1), (True, 1, 0))
    check("emb call 3", rl.allow("alice", "embeddings", 2), (True, 0, 0))


def test_mixed_strategies():
    rl = RateLimiter({"gpt": ("TokenBucket", {"capacity": 2, "rate": 1}),
                      "embeddings": ("SlidingWindow", {"limit": 1, "window": 10})})
    check("mixed gpt t=0", rl.allow("alice", "gpt", 0), (True, 1, 0))
    check("mixed emb t=0", rl.allow("alice", "embeddings", 0), (True, 0, 0))
    check("mixed emb t=1 rejected", rl.allow("alice", "embeddings", 1), (False, 0, 9))
    check("mixed gpt t=1", rl.allow("alice", "gpt", 1), (True, 1, 0))


def test_bad_strategy():
    try:
        RateLimiter({"gpt": ("Nope", {})})
    except ValueError:
        print("ok: bad strategy raises")
    else:
        raise AssertionError("FAIL: bad strategy did not raise")


def test_unknown_resource():
    rl = RateLimiter({"gpt": ("SlidingWindow", {"limit": 1, "window": 10})})
    try:
        rl.allow("alice", "images", 0)
    except ValueError:
        print("ok: unknown resource raises")
    else:
        raise AssertionError("FAIL: unknown resource did not raise")


def test_concurrency():
    for round_number in range(100):
        rl = RateLimiter({"gpt": ("SlidingWindow", {"limit": 3, "window": 10})})

        def worker(i):
            rl.allow(f"client{i % 4}", "gpt", 0)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for c in range(4):
            stats = rl.get_stats(f"client{c}", "gpt")
            assert stats == {"accepted": 3, "rejected": 2}, \
                f"FAIL round {round_number}, client{c}: {stats}"
    print("ok: concurrency (100 rounds)")


test_isolation()
test_expiry()
test_token_bucket()
test_stats()
test_different_limits_per_resource()
test_mixed_strategies()
test_bad_strategy()
test_unknown_resource()
test_concurrency()
print("all tests passed")