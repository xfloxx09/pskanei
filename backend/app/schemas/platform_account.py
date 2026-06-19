from pydantic import BaseModel


class PlatformAccountOut(BaseModel):
    id: str
    name: str
    connected: bool
    dailyCap: int
    enabled: bool

    model_config = {"from_attributes": True}


class PlatformSaveRequest(BaseModel):
    platforms: list[PlatformAccountOut]


class PlatformConnectResponse(BaseModel):
    url: str
