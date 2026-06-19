from pydantic import BaseModel


class ProviderItemIn(BaseModel):
    id: str
    name: str
    role: str
    apiKey: str = ""
    endpoint: str = ""
    enabled: bool = False


class ProviderItemOut(BaseModel):
    id: str
    name: str
    role: str
    apiKey: str  # masked
    endpoint: str = ""
    enabled: bool = False


class ProvidersSaveRequest(BaseModel):
    providers: list[ProviderItemIn]
    daily_budget: float = 15.0


class ProvidersResponse(BaseModel):
    providers: list[ProviderItemOut]
    daily_budget: float
