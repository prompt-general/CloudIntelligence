from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import logging
from app.models.cloud_account import CloudAccount
from app.models.resource import Resource

logger = logging.getLogger(__name__)

class GCPScanner:
    """Discovery and security scanner for Google Cloud Provider."""
    
    def __init__(self, db):
        self.db = db

    async def scan_account(self, account: CloudAccount):
        """Perform discovery and security scan on a GCP account."""
        logger.info(f"Scanning GCP account: {account.account_ref}")
        
        # In a real implementation, we would use google-cloud-sdk
        # For this M4 milestone, we implement the core discovery logic
        
        resources = []
        findings = []
        
        try:
            # Discovery: Compute Engine
            gce_resources = await self._discover_compute_engine(account)
            resources.extend(gce_resources)
            
            # Discovery: Cloud Storage
            gcs_resources = await self._discover_cloud_storage(account)
            resources.extend(gcs_resources)
            
            # Discovery: Cloud IAM
            iam_resources = await self._discover_iam(account)
            resources.extend(iam_resources)
            
            # Security Scanning
            for resource in resources:
                resource_findings = await self._scan_resource_security(resource, account)
                findings.extend(resource_findings)
                
        except Exception as e:
            logger.error(f"Error scanning GCP account {account.account_ref}: {e}")
            
        return resources, findings

    async def _discover_compute_engine(self, account: CloudAccount) -> List[Dict[str, Any]]:
        """Discover GCE instances."""
        # Mock discovery for GCE
        return [
            {
                "id": f"projects/{account.account_ref}/zones/us-central1-a/instances/web-server-gcp",
                "name": "web-server-gcp",
                "type": "gcp:compute:instance",
                "region": "us-central1",
                "properties": {
                    "machine_type": "n1-standard-1",
                    "status": "RUNNING",
                    "network_interfaces": [{"networkIP": "10.128.0.2", "accessConfigs": [{"natIP": "35.192.0.1"}]}]
                }
            }
        ]

    async def _discover_cloud_storage(self, account: CloudAccount) -> List[Dict[str, Any]]:
        """Discover GCS buckets."""
        return [
            {
                "id": f"projects/_/buckets/gcp-data-{account.account_ref}",
                "name": f"gcp-data-{account.account_ref}",
                "type": "gcp:storage:bucket",
                "region": "US",
                "properties": {
                    "storage_class": "STANDARD",
                    "iam_config": {"public_access_prevention": "inherited"}
                }
            }
        ]

    async def _discover_iam(self, account: CloudAccount) -> List[Dict[str, Any]]:
        """Discover IAM service accounts and policies."""
        return [
            {
                "id": f"projects/{account.account_ref}/serviceAccounts/cloud-intelligence-sa",
                "name": "cloud-intelligence-sa",
                "type": "gcp:iam:serviceAccount",
                "region": "global",
                "properties": {
                    "email": f"cloud-intelligence-sa@{account.account_ref}.iam.gserviceaccount.com",
                    "disabled": False
                }
            }
        ]

    async def _scan_resource_security(self, resource: Dict[str, Any], account: CloudAccount) -> List[Dict[str, Any]]:
        """Analyze a GCP resource for security vulnerabilities."""
        findings = []
        
        res_type = resource["type"]
        props = resource["properties"]
        
        if res_type == "gcp:compute:instance":
            # Check for public IP
            for ni in props.get("network_interfaces", []):
                for ac in ni.get("access_configs", []):
                    if ac.get("natIP"):
                        findings.append({
                            "rule_id": "GCP_GCE_PUBLIC_IP",
                            "severity": "medium",
                            "title": "GCE Instance with Public IP",
                            "description": f"Instance {resource['name']} has a public IP address"
                        })
                        
        elif res_type == "gcp:storage:bucket":
            # Check for public access
            if props.get("iam_config", {}).get("public_access_prevention") != "enforced":
                findings.append({
                    "rule_id": "GCP_GCS_PUBLIC_ACCESS",
                    "severity": "high",
                    "title": "GCS Bucket without Public Access Prevention",
                    "description": f"Bucket {resource['name']} does not have public access prevention enforced"
                })
                
        return findings
