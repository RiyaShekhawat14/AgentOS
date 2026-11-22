from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Tool names an agent can be given. R3 (tools/) will implement these same names.
ALLOWED_TOOLS = ("web_search", "calculator", "csv_reader", "code")

PermissionMode = Literal["auto", "ask", "blocked"]


class AgentIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    instructions: str = ""
    tools: list[str] = Field(default_factory=list)
    permissions: dict[str, PermissionMode] = Field(default_factory=dict)
    schedule: str | None = Field(default=None, max_length=100)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("tools")
    @classmethod
    def tools_known(cls, v: list[str]) -> list[str]:
        unknown = [t for t in v if t not in ALLOWED_TOOLS]
        if unknown:
            raise ValueError(f"Unknown tool(s): {', '.join(unknown)}")
        return list(dict.fromkeys(v))  # remove duplicates, keep order

    @field_validator("permissions")
    @classmethod
    def permission_tools_known(cls, v: dict) -> dict:
        unknown = [t for t in v if t not in ALLOWED_TOOLS]
        if unknown:
            raise ValueError(f"Unknown tool(s) in permissions: {', '.join(unknown)}")
        return v


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    instructions: str
    tools: list[str]
    permissions: dict[str, str]
    schedule: str | None
