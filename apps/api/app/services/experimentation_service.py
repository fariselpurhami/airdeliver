"""Versioned experiment assignment only. No exposure or outcome is fabricated."""
from types import MappingProxyType
from typing import Mapping
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.services.feature_flags import FeatureFlags,stable_bucket,valid_user


class Experiment(BaseModel):
    model_config=ConfigDict(frozen=True,extra='forbid')
    version: str=Field(min_length=1,max_length=128)
    variants: tuple[str,...]=Field(min_length=2,max_length=32)

    @field_validator('variants')
    @classmethod
    def unique_names(cls,values):
        if len(set(values))!=len(values) or any(not v.strip() or len(v)>128 or v=='control' for v in values):
            raise ValueError('Variants must be unique nonempty names; control is reserved for unassigned')
        return values


class Assignment(BaseModel):
    model_config=ConfigDict(frozen=True)
    experiment: str
    version: str|None=None
    variant: str='control'
    assigned: bool=False


class ExperimentationService:
    def __init__(self,flags: Mapping|None=None,experiments: Mapping|None=None):
        self._flags=FeatureFlags({'enable-new-product-card':True} if flags is None else flags)
        parsed={}
        for name,value in (experiments or {}).items():
            if not isinstance(name,str) or not name.strip() or len(name)>128:raise ValueError('Invalid experiment name')
            parsed[name]=value if isinstance(value,Experiment) else Experiment.model_validate(value)
        self._experiments=MappingProxyType(parsed)

    def is_feature_enabled(self,flag_name: str,user_id: int|None=None) -> bool:
        # Without a user, only globally enabled flags apply, never a rollout.
        if user_id is None:
            return self._flags.is_global_enabled(flag_name)
        return self._flags.is_enabled(flag_name,user_id)

    def get_assignment(self,user_id: int,experiment_name: str) -> Assignment:
        if not isinstance(experiment_name,str):raise ValueError('Experiment name must be a string')
        experiment=self._experiments.get(experiment_name)
        if experiment is None or not valid_user(user_id):return Assignment(experiment=experiment_name)
        bucket=stable_bucket('experiment:'+experiment_name+':'+experiment.version,user_id,slots=len(experiment.variants))
        return Assignment(experiment=experiment_name,version=experiment.version,variant=experiment.variants[bucket],assigned=True)

    def get_user_variant(self,user_id: int,experiment_name: str) -> str:
        return self.get_assignment(user_id,experiment_name).variant


experimentation_service=ExperimentationService()
