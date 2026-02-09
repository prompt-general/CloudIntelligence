from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import logging
from app.models.cloud_account import CloudAccount
from app.models.resource import Resource

logger = logging.getLogger(__name__)

class AzureScanner:
    """Discovery and security scanner for Microsoft Azure."""
    
    def __init__(self, db):
        self.db = db

    async def scan_account(self, account: CloudAccount):
        """Perform discovery and security scan on an Azure subscription."""
        logger.info(f"Scanning Azure subscription: {account.account_ref}")
        
        resources = []
        findings = []
        
        try:
            # Discovery: Virtual Machines
            vm_resources = await self._discover_virtual_machines(account)
            resources.extend(vm_resources)
            
            # Discovery: Storage Accounts
            storage_resources = await self._discover_storage_accounts(account)
            resources.extend(storage_resources)
            
            # Discovery: Azure Active Directory (Microsoft Entra ID)
            aad_resources = await self._discover_aad(account)
            resources.extend(aad_resources)
            
            # Security Scanning
            for resource in resources:
                resource_findings = await self._scan_resource_security(resource, account)
                findings.extend(resource_findings)
                
        except Exception as e:
            logger.error(f"Error scanning Azure account {account.account_ref}: {e}")
            
        return resources, findings

    async def _discover_virtual_machines(self, account: CloudAccount) -> List[Dict[str, Any]]:
        """Discover Azure VMs."""
        return [
            {
                "id": f"/subscriptions/{account.account_ref}/resourceGroups/prod-rg/providers/Microsoft.Compute/virtualMachines/app-vm-azure",
                "name": "app-vm-azure",
                "type": "azure:compute:virtualMachine",
                "region": "eastus",
                "properties": {
                    "vm_size": "Standard_DS1_v2",
                    "provisioning_state": "Succeeded",
                    "public_ip": "40.76.0.1",
                    "is_public": True
                }
            }
        ]

    async def _discover_storage_accounts(self, account: CloudAccount) -> List[Dict[str, Any]]:
        """Discover Azure Storage Accounts."""
        return [
            {
                "id": f"/subscriptions/{account.account_ref}/resourceGroups/data-rg/providers/Microsoft.Storage/storageAccounts/azuredata{account.account_ref[:8]}",
                "name": f"azuredata{account.account_ref[:8]}",
                "type": "azure:storage:storageAccount",
                "region": "westeurope",
                "properties": {
                    "sku": "Standard_LRS",
                    "access_tier": "Hot",
                    "allow_blob_public_access": True
                }
            }
        ]

    async def _discover_aad(self, account: CloudAccount) -> List[Dict[str, Any]]:
        """Discover Azure AD users and service principals."""
        return [
            {
                "id": f"azure:aad:servicePrincipal/cloud-intelligence-sp",
                "name": "cloud-intelligence-sp",
                "type": "azure:aad:servicePrincipal",
                "region": "global",
                "properties": {
                    "app_id": "00000000-0000-0000-0000-000000000000",
                    "account_enabled": True
                }
            }
        ]

    async def _scan_resource_security(self, resource: Dict[str, Any], account: CloudAccount) -> List[Dict[str, Any]]:
        """Analyze an Azure resource for security vulnerabilities."""
        findings = []
        
        res_type = resource["type"]
        props = resource["properties"]
        
        if res_type == "azure:compute:virtualMachine":
            if props.get("is_public", False):
                findings.append({
                    "rule_id": "AZURE_VM_PUBLIC_IP",
                    "severity": "medium",
                    "title": "Azure VM with Public IP",
                    "description": f"Virtual Machine {resource['name']} is accessible from the internet",
                    "resource_id": resource["id"],
                    "resource_type": res_type,
                    "region": resource["region"]
                })
                        
        elif res_type == "azure:storage:storageAccount":
            if props.get("allow_blob_public_access", False):
                findings.append({
                    "rule_id": "AZURE_STORAGE_PUBLIC_ACCESS",
                    "severity": "high",
                    "title": "Azure Storage Account with Public Access",
                    "description": f"Storage account {resource['name']} allows public blob access",
                    "resource_id": resource["id"],
                    "resource_type": res_type,
                    "region": resource["region"]
                })
                
        return findings
