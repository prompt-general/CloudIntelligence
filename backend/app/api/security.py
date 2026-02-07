from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.services.security.scanner import SecurityScanner, SecurityFinding
from app.services.security.attack_path import AttackPathAnalyzer
from app.services.alerting import AlertManager
from pydantic import BaseModel

router = APIRouter(prefix="/security", tags=["security"])

class SecurityScanRequest(BaseModel):
    scan_type: str = "full"  # full, quick, targeted
    notify: bool = True

class SecurityFindingUpdate(BaseModel):
    status: str  # open, investigating, remediated, accepted, false_positive
    notes: Optional[str] = None

@router.get("/findings")
async def get_security_findings(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(100, description="Limit results"),
    offset: int = Query(0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get security findings for the organization."""
    
    scanner = SecurityScanner(db)
    findings = await scanner.scan_organization(str(organization.id))
    
    # Apply filters
    filtered_findings = findings
    
    if severity:
        filtered_findings = [f for f in filtered_findings if f.severity.value == severity]
    
    if status:
        filtered_findings = [f for f in filtered_findings if f.status == status]
    
    if category:
        filtered_findings = [f for f in filtered_findings if f.category.value == category]
    
    if resource_type:
        filtered_findings = [f for f in filtered_findings if f.resource_type == resource_type]
    
    # Paginate
    paginated_findings = filtered_findings[offset:offset + limit]
    
    # Calculate statistics
    severity_counts = {
        "critical": len([f for f in findings if f.severity.value == "critical"]),
        "high": len([f for f in findings if f.severity.value == "high"]),
        "medium": len([f for f in findings if f.severity.value == "medium"]),
        "low": len([f for f in findings if f.severity.value == "low"])
    }
    
    category_counts = {}
    for finding in findings:
        cat = finding.category.value
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    status_counts = {}
    for finding in findings:
        stat = finding.status
        status_counts[stat] = status_counts.get(stat, 0) + 1
    
    return {
        "findings": [
            {
                "id": f.id,
                "resource_id": f.resource_id,
                "resource_type": f.resource_type,
                "account_id": f.account_id,
                "region": f.region,
                "title": f.title,
                "description": f.description,
                "severity": f.severity.value,
                "category": f.category.value,
                "remediation": f.remediation,
                "risk_score": f.risk_score,
                "status": f.status,
                "detected_at": f.detected_at.isoformat(),
                "evidence": f.evidence
            }
            for f in paginated_findings
        ],
        "pagination": {
            "total": len(filtered_findings),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < len(filtered_findings)
        },
        "statistics": {
            "total": len(findings),
            "by_severity": severity_counts,
            "by_category": category_counts,
            "by_status": status_counts
        },
        "last_scanned": datetime.utcnow().isoformat()
    }

@router.post("/scan")
async def run_security_scan(
    request: SecurityScanRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Run a security scan."""
    
    scan_id = str(uuid.uuid4())
    
    # Run scan in background
    background_tasks.add_task(
        _run_scan_background,
        scan_id,
        str(organization.id),
        request.scan_type,
        request.notify,
        db
    )
    
    return {
        "scan_id": scan_id,
        "type": request.scan_type,
        "status": "started",
        "started_at": datetime.utcnow().isoformat(),
        "organization_id": str(organization.id)
    }

async def _run_scan_background(
    scan_id: str,
    organization_id: str,
    scan_type: str,
    notify: bool,
    db: AsyncSession
):
    """Background task to run security scan."""
    scanner = SecurityScanner(db)
    
    try:
        findings = await scanner.scan_organization(organization_id)
        
        # Save findings to database (simplified)
        # In production, you would have a Findings table
        
        # Send notifications if enabled
        if notify:
            critical_findings = [f for f in findings if f.severity.value in ["critical", "high"]]
            if critical_findings:
                alert_manager = AlertManager(db)
                await alert_manager.send_security_alerts(
                    organization_id,
                    critical_findings
                )
        
        # Update attack graph
        analyzer = AttackPathAnalyzer(db)
        await analyzer.build_attack_graph(organization_id)
        
    except Exception as e:
        print(f"Error in security scan {scan_id}: {e}")

@router.get("/dashboard")
async def get_security_dashboard(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get security dashboard data."""
    
    scanner = SecurityScanner(db)
    findings = await scanner.scan_organization(str(organization.id))
    
    # Calculate security score
    open_findings = [f for f in findings if f.status == "open"]
    
    severity_weights = {
        "critical": 10,
        "high": 5,
        "medium": 2,
        "low": 1
    }
    
    weighted_score = 0
    total_weight = 0
    
    for finding in open_findings:
        weight = severity_weights.get(finding.severity.value, 1)
        weighted_score += weight
        total_weight += 1
    
    security_score = 100
    if total_weight > 0:
        security_score = max(0, 100 - (weighted_score / total_weight) * 10)
    
    # Get recent findings (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_findings = [f for f in open_findings if f.detected_at > seven_days_ago]
    
    # Get findings by resource type
    by_resource_type = {}
    for finding in open_findings:
        rt = finding.resource_type
        by_resource_type[rt] = by_resource_type.get(rt, 0) + 1
    
    # Get top risks
    top_risks = sorted(
        open_findings,
        key=lambda x: severity_weights.get(x.severity.value, 1),
        reverse=True
    )[:5]
    
    return {
        "security_score": round(security_score, 1),
        "findings_summary": {
            "total": len(open_findings),
            "critical": len([f for f in open_findings if f.severity.value == "critical"]),
            "high": len([f for f in open_findings if f.severity.value == "high"]),
            "medium": len([f for f in open_findings if f.severity.value == "medium"]),
            "low": len([f for f in open_findings if f.severity.value == "low"]),
            "new_last_7_days": len(recent_findings)
        },
        "by_resource_type": by_resource_type,
        "top_risks": [
            {
                "id": f.id,
                "title": f.title,
                "severity": f.severity.value,
                "resource_type": f.resource_type,
                "resource_id": f.resource_id,
                "risk_score": f.risk_score,
                "detected_at": f.detected_at.isoformat()
            }
            for f in top_risks
        ],
        "trend_data": _generate_trend_data(findings),
        "last_updated": datetime.utcnow().isoformat()
    }

def _generate_trend_data(findings: List[SecurityFinding]) -> List[Dict]:
    """Generate trend data for security findings."""
    trend_data = []
    
    # Generate last 30 days of data
    for i in range(30):
        date = datetime.utcnow() - timedelta(days=30 - i)
        day_findings = [
            f for f in findings 
            if f.detected_at.date() == date.date()
        ]
        
        trend_data.append({
            "date": date.isoformat(),
            "total": len(day_findings),
            "critical": len([f for f in day_findings if f.severity.value == "critical"]),
            "high": len([f for f in day_findings if f.severity.value == "high"])
        })
    
    return trend_data

@router.get("/attack-paths")
async def get_attack_paths(
    source_node: Optional[str] = Query(None, description="Source node ID"),
    target_node: Optional[str] = Query(None, description="Target node ID"),
    max_length: int = Query(5, description="Maximum path length"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get attack paths for the organization."""
    
    analyzer = AttackPathAnalyzer(db)
    
    # Build or update attack graph
    await analyzer.build_attack_graph(str(organization.id))
    
    # Find attack paths
    paths = await analyzer.find_attack_paths(
        source_node_id=source_node,
        target_node_id=target_node,
        max_path_length=max_length
    )
    
    return {
        "paths": [
            {
                "nodes": [
                    {
                        "id": node.id,
                        "type": node.type.value,
                        "name": node.name,
                        "account_id": node.account_id,
                        "region": node.region,
                        "risk_score": node.risk_score,
                        "criticality": node.criticality
                    }
                    for node in path.nodes
                ],
                "edges": [
                    {
                        "source": edge.source_id,
                        "target": edge.target_id,
                        "type": edge.type.value,
                        "weight": edge.weight
                    }
                    for edge in path.edges
                ],
                "total_risk": path.total_risk,
                "path_length": path.path_length,
                "critical_nodes": path.critical_nodes
            }
            for path in paths
        ],
        "count": len(paths),
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/attack-graph")
async def get_attack_graph(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get attack graph visualization data."""
    
    analyzer = AttackPathAnalyzer(db)
    await analyzer.build_attack_graph(str(organization.id))
    
    graph_data = analyzer.visualize_graph()
    
    # Get high risk nodes
    high_risk_nodes = await analyzer.get_high_risk_nodes(limit=20)
    
    return {
        "graph": graph_data,
        "high_risk_nodes": high_risk_nodes,
        "statistics": {
            "total_nodes": len(graph_data["nodes"]),
            "total_edges": len(graph_data["links"]),
            "high_risk_count": len([n for n in high_risk_nodes if n["risk_score"] > 70])
        }
    }

@router.get("/blast-radius/{node_id}")
async def get_blast_radius(
    node_id: str,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Calculate blast radius for a node."""
    
    analyzer = AttackPathAnalyzer(db)
    await analyzer.build_attack_graph(str(organization.id))
    
    blast_radius = await analyzer.calculate_blast_radius(node_id)
    
    return blast_radius

@router.get("/compliance")
async def get_compliance_status(
    framework: Optional[str] = Query("aws-foundational", description="Compliance framework"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get compliance status for the organization."""
    
    scanner = SecurityScanner(db)
    findings = await scanner.scan_organization(str(organization.id))
    
    # Map findings to compliance controls
    compliance_controls = _map_findings_to_compliance(findings, framework)
    
    # Calculate compliance score
    total_controls = len(compliance_controls)
    passed_controls = len([c for c in compliance_controls if c["status"] == "passed"])
    
    compliance_score = (passed_controls / total_controls * 100) if total_controls > 0 else 100
    
    return {
        "framework": framework,
        "compliance_score": round(compliance_score, 1),
        "controls": {
            "total": total_controls,
            "passed": passed_controls,
            "failed": total_controls - passed_controls
        },
        "detailed_controls": compliance_controls,
        "last_assessed": datetime.utcnow().isoformat()
    }

def _map_findings_to_compliance(findings: List[SecurityFinding], framework: str) -> List[Dict]:
    """Map security findings to compliance controls."""
    
    # Simplified compliance mapping
    # In production, this would use a proper compliance framework
    
    compliance_map = {
        "IAM_NO_MFA": {
            "control_id": "IAM.1",
            "control_name": "Multi-factor authentication",
            "description": "IAM users should have MFA enabled",
            "standard": "AWS Foundational Security Best Practices"
        },
        "S3_PUBLIC_ACL": {
            "control_id": "S3.1",
            "control_name": "S3 bucket public access",
            "description": "S3 buckets should not have public access",
            "standard": "AWS Foundational Security Best Practices"
        },
        "RDS_PUBLIC": {
            "control_id": "RDS.1",
            "control_name": "RDS public access",
            "description": "RDS instances should not be publicly accessible",
            "standard": "AWS Foundational Security Best Practices"
        }
    }
    
    controls = []
    
    # Add passed controls (no findings for these)
    for rule_id, control_info in compliance_map.items():
        control_findings = [f for f in findings if f.rule_id == rule_id and f.status == "open"]
        
        controls.append({
            "control_id": control_info["control_id"],
            "control_name": control_info["control_name"],
            "description": control_info["description"],
            "standard": control_info["standard"],
            "status": "passed" if not control_findings else "failed",
            "findings": [
                {
                    "id": f.id,
                    "title": f.title,
                    "severity": f.severity.value,
                    "resource_id": f.resource_id
                }
                for f in control_findings
            ]
        })
    
    return controls

@router.post("/findings/{finding_id}/remediate")
async def remediate_finding(
    finding_id: str,
    remediation_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Initiate remediation for a security finding."""
    
    # This would trigger remediation workflows
    # For now, return mock response
    
    return {
        "remediation_id": str(uuid.uuid4()),
        "finding_id": finding_id,
        "action": remediation_data.get("action", "manual"),
        "status": "pending_approval",
        "requested_by": current_user.email,
        "requested_at": datetime.utcnow().isoformat(),
        "estimated_completion": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }