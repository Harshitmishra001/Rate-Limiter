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
    def __init__(self, limit, window):
        self.limit = limit
        self.window = window
        self.limiters = {}
    def allow(self,client,resource,now):
        if (client,resource) not in self.limiters:
            self.limiters[(client,resource)] = SlidingWindow(self.limit,self.window)
        return self.limiters[(client,resource)].allow(now)
        
rl = RateLimiter(2, 10)
print(rl.allow("alice", "gpt", 0))         # 1
print(rl.allow("alice", "gpt", 1))         # 2
print(rl.allow("alice", "gpt", 2))         # 3
print(rl.allow("bob", "gpt", 2))           # 4
print(rl.allow("alice", "embeddings", 2))  # 5
print(rl.allow("alice", "gpt", 10))        # 6