from collections import deque
class SlidingWindow:
    def __init__(self,limit:int,window:float):
        self.limit=limit
        self.window=window
        self.timestamps = deque()
    def allow(self,now):
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
    def allow(self,now,cost=1):
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
    def __init__(self, strategy, config):
        self.strategy = strategy
        self.config = config
        self.limiters = {}
    def allow(self,client,resource,now):
        strategies = {"SlidingWindow": SlidingWindow, "TokenBucket": TokenBucket}
        if self.strategy not in strategies:
            raise ValueError("unknown strategy")
        if (client,resource) not in self.limiters:
            cls = strategies[self.strategy]
            self.limiters[(client,resource)] = cls(**self.config)
        return self.limiters[(client,resource)].allow(now)
        
sw = RateLimiter("SlidingWindow", {"limit": 2, "window": 10})
print(sw.allow("alice", "gpt", 0))   # predict
print(sw.allow("alice", "gpt", 1))   # predict
print(sw.allow("alice", "gpt", 2))   # predict

tb = RateLimiter("TokenBucket", {"capacity": 2, "rate": 1})
print(tb.allow("alice", "gpt", 0))   # predict
print(tb.allow("alice", "gpt", 0))   # predict
print(tb.allow("alice", "gpt", 0))   # predict
print(tb.allow("alice", "gpt", 1))   # predict
