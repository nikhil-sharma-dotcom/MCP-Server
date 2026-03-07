from pydantic import BaseModel, Field
from typing import Literal, Annotated, List


# ---- Finding Object ----
class Finding(BaseModel):
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    vendor:  Annotated[str, Field(min_length=1, max_length=200)]
    amount: Annotated[float, Field(ge=0)]
    category: str | None = None
    issue: str | None = None


# ---- Tool Inputs ----
class HighValueRequest(BaseModel):
    min_amount: Annotated[float, Field(ge=0)] = 10000.0


class VendorRequest(BaseModel):
    vendor_name: Annotated[str, Field(min_length=1, max_length=200)]


class AuditReportRequest(BaseModel):
    findings: Annotated[List[Finding], Field(max_length=5000)]
    flow_id: Annotated[str, Field(min_length=1, max_length=100)]
    user_id: Annotated[str, Field(min_length=1, max_length=100)]
    role: Annotated[str, Field(min_length=1, max_length=50)]