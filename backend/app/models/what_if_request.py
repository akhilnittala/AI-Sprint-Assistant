from pydantic import BaseModel


class WhatIfRequest(BaseModel):
    story_id: str
