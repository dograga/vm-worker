from google.cloud import firestore
from pydantic import BaseModel, Field

class NodePoolSizeTag(BaseModel):
    project_id: str
    zone: str
    cluster_id: str
    nodepool_id: str
    enable_autoscaling: bool
    business_hours: str = Field(..., example="3,6,4")  # min=3,max=6,desired=4
    off_hours: str = Field(..., example="0,0,0")       # min=0,max=0,desired=0

def get_doc_id(tag: NodePoolSizeTag) -> str:
    # Compose unique doc id from identifiers
    return f"{tag.project_id}__{tag.cluster_id}__{tag.nodepool_id}"

def store_nodepool_size_tag(tag: NodePoolSizeTag):
    # Initialize Firestore client
    db = firestore.Client()

    # Collection name
    collection_name = "gke-nodepool-scheduler"
    
    doc_id = get_doc_id(tag)
    doc_ref = db.collection(collection_name).document(doc_id)

    # Convert pydantic model to dict
    data = tag.dict()

    # Store or update document
    doc_ref.set(data)
    logger.info(f"Stored nodepool size tag: {data} in collection: {collection_name} with doc_id: {doc_id}")
    print(f"Stored nodepool info for doc_id: {doc_id}")

if __name__ == "__main__":
    example_tag = NodePoolSizeTag(
        project_id="extended-web-339507",
        zone="us-central1-a",
        cluster_id="cluster-1",
        nodepool_id="np-1",
        enable_autoscaling=True,
        business_hours="3,6,4",
        off_hours="0,0,0",
    )
    store_nodepool_size_tag(example_tag)
