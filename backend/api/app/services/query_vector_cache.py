"""Bounded process-local successful vectors only. No catalog/product facts.

Contract/model object identity must be included by caller. Native model gate
coalesces duplicate active work; cached tuples cannot be mutated by callers.
"""
from collections import OrderedDict
import threading,time,math

class QueryVectorCache:
    def __init__(self,capacity=128,ttl=600):
        self.capacity=capacity;self.ttl=ttl;self.rows=OrderedDict();self.lock=threading.Lock()
    def get(self,key):
        with self.lock:
            item=self.rows.get(key)
            if item is None:return None
            if item[0]<=time.monotonic():del self.rows[key];return None
            self.rows.move_to_end(key);return list(item[1])
    def put(self,key,vector,dimension):
        if len(vector)!=dimension or not all(math.isfinite(x) for x in vector) or not any(vector):return
        with self.lock:
            self.rows[key]=(time.monotonic()+self.ttl,tuple(float(x) for x in vector));self.rows.move_to_end(key)
            while len(self.rows)>self.capacity:self.rows.popitem(last=False)
