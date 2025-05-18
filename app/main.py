from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google.cloud import compute_v1
from typing import Literal
import json
import base64
import structlog
from app.gcp import perform_vm_operation

logger = structlog.get_logger()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <- Allow any domain
    allow_credentials=True,
    allow_methods=["*"],  # <- Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # <- Allow all headers
)

class VMOperationPayload(BaseModel):
    vm_name: str = Field(..., example="test-vm")
    action: Literal["start", "stop", "restart"]
    zone: str = Field(..., example="us-central1-a")
    project_id: str

@app.post("/vm-worker")
async def vm_handler(request: Request):
    try:
        envelope = await request.json()
        delivery_attempt = request.headers.get("x-goog-pubsub-delivery-attempt", "1")
        logger.info(f"Delivery Attempt: {delivery_attempt}")
        if "message" not in envelope or "data" not in envelope["message"]:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        # Decode and parse the base64-encoded message
        message = envelope.get("message", {})
        message_id = message.get("messageId")
        payload_data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        logger.info(f"Received message ID: {message_id}, Data: {payload_data}")
        payload_dict = json.loads(payload_data)
        try:
            payload = VMOperationPayload(**payload_dict)
            operation = perform_vm_operation(
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
async def vm_audit_handler(vm_op: VMOperationPayload):
    try:
        payload_dict = vm_op.dict()
        logger.info(f"Debugging VM operation: {payload_dict}")
        payload = VMOperationPayload(**payload_dict)
        logger.info(f"Debugging VM operation: {payload.vm_name} with action {payload.action} {payload.zone} {payload.project_id}")
        operation = perform_vm_operation(
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