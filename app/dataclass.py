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