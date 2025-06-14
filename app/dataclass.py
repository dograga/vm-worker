from pydantic import BaseModel, Field, field_validator
from typing_extensions import Annotated
from typing import Literal, List, Optional
import re

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

class NodePoolSizeTag(BaseModel):
    project_id: str
    zone: str
    cluster_id: str
    nodepool_id: str
    enable_autoscaling: bool
    business_hours_config: str = Field(..., example="3,6,4")  # min=3,max=6,desired=4
    off_hours_config: str = Field(..., example="0,0,0")       # min=0,max=0,desired=0
    business_hours: dict = Field(..., example={"days": [1,2,3,4], "starttime":"06:00:00", "endtime": "18:00:00", "timezone": "SGT"}) 
    updated_on: Optional[str] = None  # ISO format date string, e.g., "2023-10-01T12:00:00Z"
    updated_by: Optional[str] = None  # User who updated the tag, e.g., "


class MaintenanceWindowRequest(BaseModel):
    project_id: str
    location: str  # e.g., "us-central1"
    cluster_id: str
    frequency: Annotated[str, Field(description="Only 'WEEKLY' is allowed")]
    byday: List[str]  # e.g., ["MO", "TH"]
    start_time: str  # Format "HH:MM"
    duration_hours: int  # between 4 and 24 
    updated_on: Optional[str] = None  # ISO format date string, e.g., "2023-10-01T12:00:00Z"
    updated_by: Optional[str] = None  # User who updated the tag, e.g., "

class ScheduleTag(BaseModel):
    days: List[int] = Field(..., example=[1, 2, 3, 4, 5])
    starttime: str = Field(..., example="06:00:00")
    endtime: str = Field(..., example="20:00:00")
    timezone: str = Field(..., example="SGT")
    project_id: str
    zone: str
    instance_name: str
    updated_on: Optional[str] = None  # ISO format date string, e.g., "2023-10-01T12:00:00Z"
    updated_by: Optional[str] = None  # User who updated the tag, e.g., "

class NodePoolTag(BaseModel):
    project_id: str
    location: str
    cluster_id: str
    nodepool_id: str