from typing import List

from pydantic import BaseModel


class SafetyProfile(BaseModel):
    risks: List[str]
    prevention: List[str]


class Adventure(BaseModel):
    id: str
    title: str
    location: str
    duration: str
    intro_quote: str
    description: str
    preparation: List[str]
    steps: List[str]
    child_benefit: str
    carla_tip: str
    safety: SafetyProfile
