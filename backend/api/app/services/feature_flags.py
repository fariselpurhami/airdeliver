"""Validated in-process feature configuration. Not an account permission system."""
import hashlib
from types import MappingProxyType
from typing import Mapping
from pydantic import BaseModel, ConfigDict, Field, StrictBool


class Rollout(BaseModel):
    model_config=ConfigDict(frozen=True,extra='forbid',allow_inf_nan=False)
    enabled: StrictBool=False
    percentage: int=Field(default=0,ge=0,le=100,strict=True)


def valid_user(user_id):
    return type(user_id) is int and 0<user_id<=9223372036854775807


def stable_bucket(namespace: str,user_id: int,slots: int=10000) -> int:
    value=hashlib.sha256((namespace+'\x00'+str(user_id)).encode()).digest()
    return int.from_bytes(value[:8],'big')%slots


class FeatureFlags:
    def __init__(self,flags: Mapping|None=None):
        # Preserve legacy feature names; this foundation has no active app caller.
        source={'new-checkout-flow':(False,10),'ai-chatbot-enabled':True} if flags is None else dict(flags)
        parsed={}
        for name,value in source.items():
            if not isinstance(name,str) or not name.strip() or len(name)>128:
                raise ValueError('Flag names must be nonempty and bounded')
            if type(value) is bool:
                value=Rollout(enabled=value)
            elif isinstance(value,tuple) and len(value)==2:
                value=Rollout(enabled=value[0],percentage=value[1])
            elif not isinstance(value,Rollout):
                raise ValueError('Flag configuration must be a boolean, rollout tuple or Rollout')
            parsed[name]=value
        self._flags=MappingProxyType(parsed)

    def is_global_enabled(self,flag_name: str) -> bool:
        if not isinstance(flag_name,str):return False
        rollout=self._flags.get(flag_name)
        return bool(rollout and rollout.enabled)

    def is_enabled(self,flag_name: str,user_id: int) -> bool:
        if not valid_user(user_id) or not isinstance(flag_name,str):return False
        rollout=self._flags.get(flag_name)
        if rollout is None:return False
        return rollout.enabled or stable_bucket('flag:v1:'+flag_name,user_id)<rollout.percentage*100
