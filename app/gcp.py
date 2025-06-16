from google.cloud import compute_v1
import structlog
from google.auth import default
from google.cloud import firestore
import app.dataclass as dataclass
from fastapi import HTTPException
from time import sleep
from google.cloud import container_v1
from google.protobuf.timestamp_pb2 import Timestamp
import datetime
import os
import pytz
from app.utils.config_loader import load_config
load_config()


logger = structlog.get_logger()
credentials, _ = default()
compute_client = compute_v1.InstancesClient()
firestore_db = firestore.Client(database=os.getenv("FIRESTORE_DB"), project=os.getenv("PROJECT_ID"))

def perform_vm_operation(project_id: str, zone: str, instance_name: str, action: str):
    if action == "start":
        return compute_client.start(project=project_id, zone=zone, instance=instance_name)
    elif action == "stop":
        return compute_client.stop(project=project_id, zone=zone, instance=instance_name)
    elif action == "restart":
        return compute_client.restart(project=project_id, zone=zone, instance=instance_name)
    else:
        raise ValueError(f"Unsupported action: {action}")

def set_nodepool_desired_size(client: container_v1.ClusterManagerClient, name: str, desired_size: int):
    """
    Set the desired size of the node pool using the gRPC client.
    """
    attempts = 0
    max_retries = 3
    while attempts < max_retries:
        sleep(5)  # Wait for the cluster to stabilize
        try:
            resize_request = container_v1.SetNodePoolSizeRequest(
                name=name,
                node_count=desired_size
            )
            logger.info(f"Trying to update desired size to {desired_size} for node pool: {name}")
            resize_response = client.set_node_pool_size(request=resize_request)
            logger.info(f"Node pool resized to {desired_size} nodes")
            return "Success"
        except Exception as e:
            logger.error(f"Error resizing node pool: {e}")
            attempts += 1
    raise HTTPException(status_code=500, detail="Failed to resize node pool after multiple attempts")


def nodepool_setsize(config: dataclass.NodePoolConfig):
    """
    Configure the node pool for a GKE cluster 
    """
    try:
        client = container_v1.ClusterManagerClient()
        name = f"projects/{config.project_id}/locations/{config.zone}/clusters/{config.cluster_id}/nodePools/{config.nodepool_id}"
        logger.info(f"Configuring node pool: {name}")
        logger.info(f"Node pool config: {config}")

        if config.enable_autoscaling:
            if config.min_nodes is None or config.max_nodes is None:
                logger.error("min_nodes and max_nodes are required when autoscaling is enabled")
                raise HTTPException(status_code=400, detail="min_nodes and max_nodes are required when autoscaling is enabled")

            autoscaling_request = container_v1.SetNodePoolAutoscalingRequest(
                name=name,
                autoscaling=container_v1.NodePoolAutoscaling(
                    enabled=True,
                    min_node_count=config.min_nodes,
                    max_node_count=config.max_nodes
                )
            )
            autoscaling_response = client.set_node_pool_autoscaling(request=autoscaling_request)
            resize_response = None

            if config.desired_node_count is not None:
                resize_response = set_nodepool_desired_size(client, name, config.desired_node_count)

            return {
                "status": "autoscaler_configured",
                "autoscaler_response": "Success",
            }

        else:
            if config.desired_node_count is None:
                raise HTTPException(status_code=400, detail="desired_node_count is required when autoscaling is disabled")

            disable_autoscaling_request = container_v1.SetNodePoolAutoscalingRequest(
                name=name,
                autoscaling=container_v1.NodePoolAutoscaling(enabled=False)
            )
            autoscaling_response = client.set_node_pool_autoscaling(request=disable_autoscaling_request)

            resize_response = set_nodepool_desired_size(client, name, config.desired_node_count)

            return {
                "status": "autoscaler_disabled_and_resized",
                "autoscaler_response": autoscaling_response,
                "resize_response": resize_response
            }

    except Exception as e:
        logger.error(f"Error updating node pool: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating node pool: {str(e)}")


def make_timestamp(hour: int, minute: int) -> Timestamp:
    now = datetime.datetime.now(datetime.timezone.utc)
    dt = datetime.datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=hour,
        minute=minute,
        tzinfo=datetime.timezone.utc
    )
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts

def schedule_maintenance(req: dataclass.MaintenanceWindowRequest):
    client = container_v1.ClusterManagerClient()

    # Parse time
    try:
        hours, minutes = map(int, req.start_time.split(":"))
        end_hour = (hours + req.duration_hours) % 24

        # Create start and end timestamps
        start_ts = make_timestamp(hours, minutes)
        end_ts = make_timestamp(end_hour, minutes)
        logger.info(f"Scheduling maintenance from {start_ts.ToDatetime()} to {end_ts.ToDatetime()}")
        recurring_window = container_v1.RecurringTimeWindow(
            window=container_v1.TimeWindow(
                start_time=start_ts,
                end_time=end_ts,
            ),
            recurrence=f"FREQ={req.frequency};BYDAY={','.join(req.byday)}"
        )
        cluster = client.get_cluster(
        name=f"projects/{req.project_id}/locations/{req.location}/clusters/{req.cluster_id}"
        )
        resource_version = cluster.maintenance_policy.resource_version
        logger.info(f"Current resource version: {resource_version}")
        maintenance_policy = container_v1.MaintenancePolicy(
            window=container_v1.MaintenanceWindow(
            recurring_window=recurring_window
            ),
            resource_version=resource_version
        )
        
        request = container_v1.SetMaintenancePolicyRequest(
            name=f"projects/{req.project_id}/locations/{req.location}/clusters/{req.cluster_id}",
            maintenance_policy=maintenance_policy
        )
        response = client.set_maintenance_policy(request=request)
        logger.info(f"Maintenance scheduled successfully: {response}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error scheduling maintenance: {e}")
        raise HTTPException(status_code=500, detail=f"Error scheduling maintenance: {str(e)}")

def get_vm_doc_id(project_id, instance_name) -> str:
    """Generate Firestore document ID for a VM instance."""
    return f"{project_id}-vmid-{instance_name}"

def store_vm_schedule_tag(tag: dataclass.ScheduleTag):
    """Store VM instance schedule in Firestore."""
    #db = firestore.Client()
    collection_name = "vm-instance-schedule"
    logger.info(f"Storing VM schedule tag in collection: {collection_name}")

    try:
        doc_id = get_vm_doc_id(tag.project_id, tag.instance_name)
        doc_ref = firestore_db.collection(collection_name).document(doc_id)

        doc_data = {
            "business_hours": {
                "days": tag.days,
                "starttime": tag.starttime,
                "endtime": tag.endtime,
                "timezone": tag.timezone.lower()
            },
            "vm_name": tag.instance_name,
            "zone": tag.zone,
            "project_id": tag.project_id,
            "updated_on": datetime.datetime.now(pytz.timezone("Asia/Singapore")).isoformat(),
            "updated_by": tag.updated_by or "system",  # Default to 'system' if not provided
        }

        doc_ref.set(doc_data)
        logger.info(f"Stored VM schedule tag under doc_id: {doc_id} data: {doc_data}")

        return {
            "message": f"Schedule info stored for {tag.instance_name}",
            "document_id": doc_id,
            "collection": collection_name
        }

    except Exception as e:
        logger.error(f"Error storing VM schedule tag: {e}")
        raise HTTPException(status_code=500, detail=f"Error storing VM schedule tag: {str(e)}")

def get_nodepool_doc_id(tag: dataclass.NodePoolSizeTag) -> str:
    # Compose unique doc id from identifiers
    return f"{tag.project_id}-clid-{tag.cluster_id}-nid-{tag.nodepool_id}"

def store_nodepool_size_tag(tag: dataclass.NodePoolSizeTag):
    # Initialize Firestore client
    collection_name = "gke-nodepool-scheduler"
    logger.info(f"Storing nodepool size tag in collection: {collection_name}")
    try:
        doc_id = get_nodepool_doc_id(tag)
        doc_ref = firestore_db.collection(collection_name).document(doc_id)

        # Convert pydantic model to dict
        doc_data = {
            "business_hours": tag.business_hours,
            "cluster_id": tag.cluster_id,
            "nodepool_id": tag.nodepool_id,
            "project_id": tag.project_id,
            "zone": tag.zone,
            "enable_autoscaling": tag.enable_autoscaling,
            "business_hours_config": tag.business_hours_config,  # e.g., "3,6,4"
            "off_hours_config": tag.off_hours_config,  # e.g., "0,0,0"
            "updated_on": datetime.datetime.now(pytz.timezone("Asia/Singapore")).isoformat(),
            "updated_by": tag.updated_by or "system",  # Default to 'system' if not provided
        }
        doc_ref.set(doc_data)
        return {
            "message": f"Schedule info stored for {tag.nodepool_id}",
            "document_id": doc_id,
            "collection": collection_name
        }
        logger.info(f"Stored nodepool info for doc_id: {doc_id}")
    except Exception as e:
        logger.error(f"Error storing nodepool size tag: {e}")
        raise HTTPException(status_code=500, detail=f"Error storing nodepool size tag: {str(e)}")

def delete_nodepool_tag(tag: dataclass.NodePoolDelete):
    """Delete a node pool size tag from Firestore."""
    collection_name = "gke-nodepool-scheduler"
    logger.info(f"Deleting nodepool size tag in collection: {collection_name}")
    try:
        doc_id = get_nodepool_doc_id(tag)
        doc_ref = firestore_db.collection(collection_name).document(doc_id)
        doc_ref.delete()
        logger.info(f"Deleted nodepool size tag with doc_id: {doc_id}")
        return {"message": f"Node pool size tag deleted for {tag.nodepool_id}", "document_id": doc_id}
    except Exception as e:
        logger.error(f"Error deleting nodepool size tag: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting nodepool size tag: {str(e)}")
    
def delete_vm_schedule(tag: dataclass.VMScheduleDelete):
    """Delete a node pool size tag from Firestore."""
    collection_name = "gke-nodepool-scheduler"
    logger.info(f"Deleting nodepool size tag in collection: {collection_name}")
    try:
        doc_id = get_vm_doc_id(tag.project_id, tag.instance_name)
        doc_ref = firestore_db.collection(collection_name).document(doc_id)
        doc_ref.delete()
        logger.info(f"Deleted VM schedule with doc_id: {doc_id}")
        return {"message": f"VM Schedule deleted for {tag.instance_name}", "document_id": doc_id}
    except Exception as e:
        logger.error(f"Error deleting nodepool size tag: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting nodepool size tag: {str(e)}")