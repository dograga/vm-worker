from pydantic import BaseModel, Field
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

