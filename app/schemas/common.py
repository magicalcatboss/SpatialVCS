from typing import TypeAlias

from pydantic import BaseModel, ConfigDict


BoundingBox: TypeAlias = list[int]


class Position3D(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Pose(BaseModel):
    alpha: float = 0.0
    beta: float = 0.0
    gamma: float = 0.0


class AliasModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
