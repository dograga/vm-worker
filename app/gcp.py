from google.cloud import compute_v1
import structlog
from google.auth import default
import app.dataclass as dataclass
from fastapi import HTTPException
from time import sleep
from google.cloud import container_v1

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
    Configure the node pool for a GKE cluster using the gRPC client.
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


def apply_nodepool_schedule_labels(nodepool_tag: dataclass.NodePoolSizeTag):
    """
    Apply nodepool schedule configuration as labels in the format: "min,max,desired"
    """
    try:
        client = container_v1.NodePoolsClient()
        name = f"projects/{nodepool_tag.project_id}/locations/{nodepool_tag.zone}/clusters/{nodepool_tag.cluster_id}/nodePools/{nodepool_tag.nodepool_id}"

        # Get the current node pool
        nodepool = client.get(name=name)
        existing_labels = dict(nodepool.resource_labels)
        fingerprint = nodepool.label_fingerprint

        # Prepare new labels
        existing_labels["nodepool-business-hours"] = nodepool_tag.business_hours
        existing_labels["nodepool-off-hours"] = nodepool_tag.off_hours

        # Create the SetLabels request
        request = container_v1.SetLabelsRequest(
            name=name,
            resource_labels=existing_labels,
            label_fingerprint=fingerprint
        )

        op = client.set_labels(request=request)
        logger.info(f"Labels applied: business_hours={nodepool_tag.business_hours}, off_hours={nodepool_tag.off_hours}")
        return {
            "message": "Labels updated successfully",
            "operation": op.name,
            "labels": {
                "nodepool-business-hours": nodepool_tag.business_hours,
                "nodepool-off-hours": nodepool_tag.off_hours
            }
        }

    except Exception as e:
        logger.error(f"Failed to apply labels to node pool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply labels: {str(e)}")