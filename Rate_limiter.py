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
            return True
        else:
            return False
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
        return self.tokens
