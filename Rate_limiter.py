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
b = SlidingWindow(3, 10)
print(b.allow(0))
print(b.allow(1))
print(b.allow(2))
print(b.allow(3))
print(b.allow(10))