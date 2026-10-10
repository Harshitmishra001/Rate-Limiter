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
                time.sleep(0.001)
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
                time.sleep(0.001)
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
        self.stats = {}
    def allow(self,client,resource,now):
        strategies = {"SlidingWindow": SlidingWindow, "TokenBucket": TokenBucket}
        if self.strategy not in strategies:
            raise ValueError("unknown strategy")
        if (client,resource) not in self.limiters:
            cls = strategies[self.strategy]
            self.limiters[(client,resource)] = cls(**self.config)
        if (client,resource) not in self.stats:
            self.stats[(client,resource)] = {"accepted":0,"rejected":0}
        s = self.limiters[(client,resource)].allow(now)
        if s[0] == True:
            self.stats[(client,resource)]["accepted"] +=1
        else:
            self.stats[(client,resource)]["rejected"] +=1
        return s
    def get_stats(self,client,resource):
        return f'for {client},{resource} Accepted = {self.stats[(client,resource)]["accepted"]} and Rejected = {self.stats[(client,resource)]["rejected"]}'
    
import threading
sw = SlidingWindow(3,10)
results = []
def worker():
    results.append(sw.allow(0))
threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
print(sum(1 for r in results if r[0]))
tb = TokenBucket(3, 0.001)
results = []
def worker():
    results.append(tb.allow(0))
threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
print(sum(1 for r in results if r[0]))