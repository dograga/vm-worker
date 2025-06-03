from typing import List
from pydantic.dataclasses import dataclass
from pydantic import field_validator
from google.cloud import container_v1
from google.protobuf.timestamp_pb2 import Timestamp
import datetime
import re

VALID_DAYS = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}

@dataclass
class MaintenanceWindowRequest:
    project_id: str
    location: str
    cluster_id: str
    frequency: str
    byday: List[str]
    start_time: str
    duration_hours: int

    @field_validator("frequency")
    @classmethod
    def frequency_must_be_weekly(cls, v):
        if v != "WEEKLY":
            raise ValueError("Only 'WEEKLY' frequency is supported")
        return v

    @field_validator("byday")
    @classmethod
    def validate_days(cls, v):
        invalid = [d for d in v if d not in VALID_DAYS]
        if invalid:
            raise ValueError(f"Invalid days: {invalid}")
        return v

    @field_validator("start_time")
    @classmethod
    def validate_time_format(cls, v):
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("start_time must be in HH:MM format")
        return v

    @field_validator("duration_hours")
    @classmethod
    def validate_duration(cls, v):
        if v < 4 or v > 24:
            raise ValueError("duration_hours must be between 4 and 24")
        return v

def make_timestamp(hour: int, minute: int) -> Timestamp:
    #now = datetime.datetime.utcnow()
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

def schedule_maintenance(req: MaintenanceWindowRequest):
    client = container_v1.ClusterManagerClient()

    # Parse time
    hours, minutes = map(int, req.start_time.split(":"))
    end_hour = (hours + req.duration_hours) % 24

    # Create start and end timestamps
    start_ts = make_timestamp(hours, minutes)
    end_ts = make_timestamp(end_hour, minutes)

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
    return response

# Example usage
if __name__ == "__main__":
    x = MaintenanceWindowRequest(
        project_id="extended-web-339507",
        location="us-central1-a",
        cluster_id="my-private-cluster-1",
        frequency="WEEKLY",
        byday=["MO", "TH"],
        start_time="03:00",
        duration_hours=6
    )
    print(schedule_maintenance(x))
