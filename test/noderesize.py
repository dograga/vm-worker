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

def get_doc_id(tag: NodePoolSizeTag) -> str:
    return f"{tag.project_id}__{tag.cluster_id}__{tag.nodepool_id}"

def store_nodepool_size_tag(tag: NodePoolSizeTag):
    db = firestore.Client()
    collection_name = "gke-nodepool-scheduler"
    doc_id = get_doc_id(tag)
    doc_ref = db.collection(collection_name).document(doc_id)

    # 🔄 Use model_dump instead of dict (for Pydantic v2)
    data = tag.model_dump()

    doc_ref.set(data)
    print(f"Stored nodepool info for doc_id: {doc_id}")

if __name__ == "__main__":
    data = {"project_id": "extended-web-339507", "zone": "us-central-1", "cluster_id": "my-private-cluster-1", "nodepool_id": "default-pool", "enable_autoscaling": true, "business_hours": {"days": [1, 2, 3, 4], "endtime": "18:00:00", "starttime": "06:00:00"}, "business_hours_config": "1,1,1", "off_hours_config": "0,0,0", "job_id": "cf9055dd-318f-45ec-925f-e4ec35eaaef5"}
    example_tag = NodePoolSizeTag(
        project_id="extended-web-339507",
        zone="us-central1-a",
        cluster_id="cluster-1",
        nodepool_id="np-1",
        enable_autoscaling=True,
        business_hours_config="3,6,4",
        off_hours_config="0,0,0",
        business_hours={"days": [1, 2, 3, 4], "starttime": "06:00:00", "endtime": "18:00:00"}
    )
    store_nodepool_size_tag(example_tag)
