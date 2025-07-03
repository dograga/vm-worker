import google.auth
from google.cloud import securitycenter_v1
from googleapiclient import discovery

# Authenticate using default credentials
credentials, project_id = google.auth.default()

def list_gke_clusters(project_id):
    container_service = discovery.build('container', 'v1', credentials=credentials)
    request = container_service.projects().zones().clusters().list(projectId=project_id, zone='-')
    response = request.execute()
    clusters = response.get('clusters', [])
    return clusters

def fetch_vulnerabilities(project_id):
    client = securitycenter_v1.SecurityCenterClient()

    parent = f"projects/{project_id}/sources/-"
    filter_expr = (
        'category="VULNERABILITY" AND state="ACTIVE"'
    )

    findings = client.list_findings(
        request={
            "parent": parent,
            "filter": filter_expr,
        }
    )

    vulns = []
    for finding in findings:
        resource_name = finding.finding.resource_name
        if "container" in resource_name or "gke" in resource_name:
            vulns.append({
                "name": finding.finding.name,
                "severity": finding.finding.severity,
                "category": finding.finding.category,
                "resource": resource_name,
                "event_time": finding.finding.event_time
            })
    return vulns

def main():
    print(f"📦 Fetching GKE clusters in project: {project_id}")
    clusters = list_gke_clusters(project_id)
    if not clusters:
        print("❌ No GKE clusters found.")
        return

    for cluster in clusters:
        name = cluster['name']
        location = cluster['location']
        print(f"\n🔍 Checking vulnerabilities for cluster: {name} ({location})")

        vulns = fetch_vulnerabilities(project_id)
        if vulns:
            for v in vulns:
                print(f"⚠️  [{v['severity']}] {v['category']} on {v['resource']} (Time: {v['event_time']})")
        else:
            print("✅ No active vulnerabilities found.")

if __name__ == "__main__":
    main()
