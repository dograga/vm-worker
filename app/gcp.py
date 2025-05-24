from google.cloud import compute_v1
import structlog
from googleapiclient.discovery import build
from google.auth import default
from app.dataclass import NodePoolConfig
from fastapi import HTTPException
from time import sleep

logger = structlog.get_logger()
credentials, _ = default()
compute_client = compute_v1.InstancesClient()

def perform_vm_operation(project_id: str, zone: str, instance_name: str, action: str):
    if action == "start":
        return compute_client.start(project=project_id, zone=zone, instance=instance_name)
    elif action == "stop":
        return compute_client.stop(project=project_id, zone=zone, instance=instance_name)
    elif action == "restart":
        return compute_client.restart(project=project_id, zone=zone, instance=instance_name)
    else:
        raise ValueError(f"Unsupported action: {action}")

def set_nodepool_desired_size(service, name: str, desired_size: int):
    """
    Set the desired size of the node pool.
    """
    sleep(15)  # Wait for the cluster to be ready
    attempts = 0
    max_retries = 3
    while attempts < max_retries:
        try:
            size_body = {
                "nodeCount": desired_size
            }
            resize_response = service.projects().locations().clusters().nodePools() \
                            .setSize(name=name, body=size_body).execute()
            logger.info(f"Node pool resized to {desired_size} nodes")
            return resize_response
        except Exception as e:
            logger.error(f"Error resizing node pool: {e}")
            attempts += 1
    if attempts == max_retries:
        raise HTTPException(status_code=500, detail="Failed to resize node pool after multiple attempts")
    
def nodepool_setsize(config: NodePoolConfig):
    """
    Configure the node pool for a GKE cluster.
    """
    try:
        service = build('container', 'v1', credentials=credentials)
        name = f"projects/{config.project_id}/locations/{config.zone}/clusters/{config.cluster_id}/nodePools/{config.nodepool_id}"
        logger.info(f"Configuring node pool: {name}")
        logger.info(f"Node pool config: {config}")
        # Autoscaling logic
        if config.enable_autoscaling:
            if config.min_nodes is None or config.max_nodes is None:
                logger.error("min_nodes and max_nodes are required when autoscaling is enabled")
                raise HTTPException(status_code=400, detail="min_nodes and max_nodes are required when autoscaling is enabled")
            
            autoscaling_body = {
                "autoscaling": {
                    "enabled": True,
                    "minNodeCount": config.min_nodes,
                    "maxNodeCount": config.max_nodes
                }
            }

            autoscaling_response = service.projects().locations().clusters().nodePools() \
                .setAutoscaling(name=name, body=autoscaling_body).execute()
            logger.info(f"Autoscaler configured with min: {config.min_nodes}, max: {config.max_nodes}")
            resize_response = None
            if config.desired_node_count is not None:
                set_nodepool_desired_size(service, name, config.desired_node_count)
            return {
                "status": "autoscaler_configured",
                "autoscaler_response": autoscaling_response,
                "resize_response": resize_response
            }

        # Manual scaling (autoscaling disabled)
        else:
            if config.desired_node_count is None:
                raise HTTPException(status_code=400, detail="desired_node_count is required when autoscaling is disabled")

            autoscaling_body = {
                "autoscaling": {
                    "enabled": False
                }
            }

            autoscaling_response = service.projects().locations().clusters().nodePools() \
                .setAutoscaling(name=name, body=autoscaling_body).execute()

            size_body = {"nodeCount": config.desired_node_count}
            resize_response = service.projects().locations().clusters().nodePools() \
                .setSize(name=name, body=size_body).execute()

            return {
                "status": "autoscaler_disabled_and_resized",
                "autoscaler_response": autoscaling_response,
                "resize_response": resize_response
            }

    except Exception as e:
        logger.error(f"Error updating node pool: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating node pool: {str(e)}")
    
