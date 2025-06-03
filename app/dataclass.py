from pydantic import BaseModel, Field, field_validator
from typing_extensions import Annotated
from typing import Literal, List, Optional

class VMOperationPayload(BaseModel):
    vm_name: str = Field(..., example="test-vm")
    action: Literal["start", "stop", "restart"]
    zone: str = Field(..., example="us-central1-a")
    project_id: str


class NodePoolConfig(BaseModel):
    project_id: str
    zone: str
    cluster_id: str
    nodepool_id: str
    enable_autoscaling: bool
    min_nodes: Optional[int] = None
    max_nodes: Optional[int] = None
    desired_node_count: Optional[int] = None

from google.cloud import firestore
from pydantic import BaseModel, Field

class NodePoolSizeTag(BaseModel):
    project_id: str
    zone: str
    cluster_id: str
    nodepool_id: str
    enable_autoscaling: bool
    business_hours_config: str = Field(..., example="3,6,4")  # min=3,max=6,desired=4
    off_hours_config: str = Field(..., example="0,0,0")       # min=0,max=0,desired=0
    business_hours: dict = Field(..., example={"days": [1,2,3,4], "starttime":"06:00:00", "endtime": "18:00:00"}) 

VALID_DAYS = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}

class MaintenanceWindowRequest(BaseModel):
    project_id: str
    location: str  # e.g., "us-central1"
    cluster_id: str
    frequency: Annotated[str, Field(description="Only 'WEEKLY' is allowed")]
    byday: List[str]  # e.g., ["MO", "TH"]
    start_time: str  # Format "HH:MM"
    duration_hours: int  # between 4 and 24

    @field_validator("frequency")
    @classmethod
    def frequency_must_be_weekly(cls, v):
        if v != "WEEKLY":
            raise ValueError("Only 'WEEKLY' frequency is supported")
        return v

    @field_validator("byday")
    @classmethod
    def validate_days(cls, v):
        invalid = [d for d in v if d not in VALID_DAYS]
        if invalid:
            raise ValueError(f"Invalid days: {invalid}")
        return v

    @field_validator("start_time")
    @classmethod
    def validate_time_format(cls, v):
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("start_time must be in HH:MM format")
        return v

    @field_validator("duration_hours")
    @classmethod
    def validate_duration(cls, v):
        if not (4 <= v <= 24):
            raise ValueError("duration_hours must be between 4 and 24")
        return v