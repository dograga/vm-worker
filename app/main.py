from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
import json
import base64
import structlog
import app.gcp as gcp
import app.dataclass as dataclass

logger = structlog.get_logger()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <- Allow any domain
    allow_credentials=True,
    allow_methods=["*"],  # <- Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # <- Allow all headers
)

@app.post("/vm-worker")
async def vm_handler(request: Request):
    ### Handle incoming Pub/Sub messages for VM operations
    try:
        envelope = await request.json()
        if "message" not in envelope or "data" not in envelope["message"]:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        # Decode and parse the base64-encoded message
        message = envelope.get("message", {})
        message_id = message.get("messageId")
        payload_data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        logger.info(f"Received message ID: {message_id}, Data: {payload_data}")
        payload_dict = json.loads(payload_data)
        try:
            payload = dataclass.VMOperationPayload(**payload_dict)
            operation = gcp.perform_vm_operation(
                project_id=payload.project_id,
                zone=payload.zone,
                instance_name=payload.vm_name,
                action=payload.action
            )
            logger.info(f"Requested VM operation '{payload.action}' for '{payload.vm_name}'")
            return {"status": "VM operation initiated"}

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    except HTTPException as http_exc:
        raise http_exc

@app.post("/vm-worker/debug")
async def vm_audit_handler(vm_op: dataclass.VMOperationPayload):
    ### Debugging endpoint for VM operations
    try:
        payload_dict = vm_op.dict()
        logger.info(f"Debugging VM operation: {payload_dict}")
        payload = dataclass.VMOperationPayload(**payload_dict)
        logger.info(f"Debugging VM operation: {payload.vm_name} with action {payload.action} {payload.zone} {payload.project_id}")
        operation = gcp.perform_vm_operation(
            project_id=payload.project_id,
            zone=payload.zone,
            instance_name=payload.vm_name,
            action=payload.action
        )
        logger.info(f"Requested VM operation '{operation}'")
        # Simulate a successful operation for debugging
        return {"status": "VM operation initiated"}
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
    
@app.post("/configure-nodepool")
async def configure_nodepool(request: Request):
    ### Handle incoming Pub/Sub messages for GKE node pool configuration
    try:
        envelope = await request.json()
        if "message" not in envelope or "data" not in envelope["message"]:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        # Decode and parse the base64-encoded message
        message = envelope.get("message", {})
        message_id = message.get("messageId")
        payload_data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        logger.info(f"Received message ID: {message_id}, Data: {payload_data}")
        payload_dict = json.loads(payload_data)
        payload = dataclass.NodePoolConfig(**payload_dict)
        response = gcp.nodepool_setsize(payload)
        return response
    except Exception as e:
        logger.error(f"Error configuring node pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/nodepool-schedule-tag")
async def nodepool_schedule_tag(request: Request):
    ### Handle incoming Pub/Sub messages for GKE node pool scheduling tags
    try:
        envelope = await request.json()
        if "message" not in envelope or "data" not in envelope["message"]:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        # Decode and parse the base64-encoded message
        message = envelope.get("message", {})
        message_id = message.get("messageId")
        payload_data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        logger.info(f"Received message ID: {message_id}, Data: {payload_data}")
        payload_dict = json.loads(payload_data)
        payload = dataclass.NodePoolSizeTag(**payload_dict)
        response = gcp.store_nodepool_size_tag(payload)
        return response
    except Exception as e:
        logger.error(f"Error configuring node pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gke-maintenance-window")
async def nodepool_schedule_tag(request: Request):
    try:
        envelope = await request.json()
        if "message" not in envelope or "data" not in envelope["message"]:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        # Decode and parse the base64-encoded message
        message = envelope.get("message", {})
        message_id = message.get("messageId")
        payload_data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        logger.info(f"Received message ID: {message_id}, Data: {payload_data}")
        payload_dict = json.loads(payload_data)
        payload = dataclass.MaintenanceWindowRequest(**payload_dict)
        response = gcp.schedule_maintenance(payload)
        return response
    except Exception as e:
        logger.error(f"Error configuring node pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vm-schedule-tag")
async def vm_schedule_tag(request: Request):
    try:
        envelope = await request.json()
        if "message" not in envelope or "data" not in envelope["message"]:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        # Decode and parse the base64-encoded message
        message = envelope.get("message", {})
        message_id = message.get("messageId")
        payload_data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        logger.info(f"Received message ID: {message_id}, Data: {payload_data}")
        payload_dict = json.loads(payload_data)
        payload = dataclass.ScheduleTag(**payload_dict)
        response = gcp.store_vm_schedule_tag(payload)
        return response
    except Exception as e:
        logger.error(f"Error configuring node pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/nodepool-delete-tag")
async def nodepool_delete_tag(request: Request):
    try:
        envelope = await request.json()
        if "message" not in envelope or "data" not in envelope["message"]:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        # Decode and parse the base64-encoded message
        message = envelope.get("message", {})
        message_id = message.get("messageId")
        payload_data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        logger.info(f"Received message ID: {message_id}, Data: {payload_data}")
        payload_dict = json.loads(payload_data)
        payload = dataclass.NodePoolDelete(**payload_dict)
        response = gcp.delete_nodepool_tag(payload)
        return response
    except Exception as e:
        logger.error(f"Error configuring node pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/vm-schedule-delete")
async def vm_schedule_delete(request: Request):
    try:
        envelope = await request.json()
        if "message" not in envelope or "data" not in envelope["message"]:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        # Decode and parse the base64-encoded message
        message = envelope.get("message", {})
        message_id = message.get("messageId")
        payload_data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        logger.info(f"Received message ID: {message_id}, Data: {payload_data}")
        payload_dict = json.loads(payload_data)
        payload = dataclass.VMScheduleDelete(**payload_dict)
        response = gcp.delete_vm_schedule(payload)
        return response
    except Exception as e:
        logger.error(f"Error configuring node pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))