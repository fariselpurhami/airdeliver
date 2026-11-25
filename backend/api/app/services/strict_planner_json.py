"""Bounded planner/reviewer JSON. Duplicate keys never silently erase evidence."""
import json

def planner_object(raw):
    if not isinstance(raw,str) or len(raw)>32768:
        raise ValueError('Invalid planner JSON boundary')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate planner JSON key')
            result[key]=value
        return result
    def constant(value):
        raise ValueError('Invalid planner numeric constant')
    try:value=json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)
    except (RecursionError,ValueError) as exc:raise ValueError('Invalid planner JSON') from exc
    if not isinstance(value,dict):raise ValueError('Planner JSON must be an object')
    return value
