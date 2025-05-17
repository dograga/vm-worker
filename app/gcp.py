from google.cloud import compute_v1

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