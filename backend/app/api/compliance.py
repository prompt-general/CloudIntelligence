from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.services.compliance.engine import (
    ComplianceEngine, 
    ComplianceFramework,
    ControlStatus
)
from pydantic import BaseModel

router = APIRouter(prefix="/compliance", tags=["compliance"])

class ComplianceAssessmentRequest(BaseModel):
    frameworks: Optional[List[str]] = None
    force_refresh: bool = False

class EvidenceRequest(BaseModel):
    control_id: str
    framework: str
    evidence_type: Optional[str] = None

@router.get("/frameworks")
async def get_compliance_frameworks(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """Get available compliance frameworks."""
    
    frameworks = []
    
    for framework in ComplianceFramework:
        frameworks.append({
            "id": framework.value,
            "name": framework.value.upper(),
            "description": self._get_framework_description(framework),
            "controls_count": 25,  # Mock data
            "last_assessed": (datetime.utcnow() - timedelta(days=2)).isoformat()
        })
    
    return {
        "frameworks": frameworks,
        "total": len(frameworks)
    }

def _get_framework_description(self, framework: ComplianceFramework) -> str:
    """Get framework description."""
    descriptions = {
        ComplianceFramework.SOC2: "SOC 2 Trust Services Criteria for security, availability, processing integrity, confidentiality, and privacy.",
        ComplianceFramework.ISO27001: "ISO/IEC 27001 Information security management systems.",
        ComplianceFramework.HIPAA: "Health Insurance Portability and Accountability Act for healthcare data.",
        ComplianceFramework.PCIDSS: "Payment Card Industry Data Security Standard for payment card data.",
        ComplianceFramework.GDPR: "General Data Protection Regulation for EU data protection.",
        ComplianceFramework.AWSNIST: "AWS alignment with NIST Cybersecurity Framework.",
        ComplianceFramework.AWSFOUNDATIONAL: "AWS Foundational Security Best Practices."
    }
    return descriptions.get(framework, "Compliance framework")

@router.post("/assess")
async def assess_compliance(
    request: ComplianceAssessmentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Run compliance assessment."""
    
    engine = ComplianceEngine(db)
    assessment_id = str(uuid.uuid4())
    
    # Run assessment in background
    background_tasks.add_task(
        _run_compliance_assessment,
        assessment_id,
        str(organization.id),
        request.frameworks,
        db
    )
    
    return {
        "assessment_id": assessment_id,
        "organization_id": str(organization.id),
        "frameworks": request.frameworks or [f.value for f in ComplianceFramework],
        "status": "started",
        "started_at": datetime.utcnow().isoformat(),
        "estimated_completion": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    }

async def _run_compliance_assessment(
    assessment_id: str,
    organization_id: str,
    frameworks: Optional[List[str]],
    db: AsyncSession
):
    """Background task to run compliance assessment."""
    engine = ComplianceEngine(db)
    
    try:
        results = await engine.assess_organization(organization_id, frameworks)
        
        # Save results to database
        await _save_assessment_results(assessment_id, organization_id, results, db)
        
        # Generate reports
        for framework in results.keys():
            await engine.generate_compliance_report(organization_id, ComplianceFramework(framework), "json")
        
    except Exception as e:
        print(f"Error in compliance assessment {assessment_id}: {e}")

async def _save_assessment_results(
    assessment_id: str,
    organization_id: str,
    results: Dict[str, Any],
    db: AsyncSession
):
    """Save assessment results to database."""
    from app.models.compliance import ComplianceAssessment
    
    for framework_str, assessment in results.items():
        db_assessment = ComplianceAssessment(
            id=assessment_id,
            organization_id=organization_id,
            framework=framework_str,
            overall_score=assessment.overall_score,
            passed_controls=assessment.passed_controls,
            total_controls=assessment.total_controls,
            assessment_data=assessment.__dict__,
            assessed_at=datetime.utcnow()
        )
        
        db.add(db_assessment)
    
    await db.commit()

@router.get("/assessment/{framework}")
async def get_compliance_assessment(
    framework: str,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get compliance assessment results."""
    
    try:
        framework_enum = ComplianceFramework(framework)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid framework")
    
    engine = ComplianceEngine(db)
    assessment = await engine._assess_framework(str(organization.id), framework_enum)
    
    return {
        "framework": framework,
        "assessment": {
            "overall_score": assessment.overall_score,
            "passed_controls": assessment.passed_controls,
            "total_controls": assessment.total_controls,
            "last_assessed": assessment.last_assessed.isoformat(),
            "next_assessment_due": assessment.next_assessment_due.isoformat(),
            "status": "compliant" if assessment.overall_score >= 80 else "non_compliant"
        },
        "controls": [
            {
                "control_id": control_id,
                "status": assessment.status.value,
                "risk_score": assessment.risk_score,
                "automated": assessment.automated,
                "evidence_count": len(assessment.evidence),
                "failure_reasons": assessment.failure_reasons,
                "last_assessed": assessment.last_assessed.isoformat()
            }
            for control_id, assessment in assessment.assessments.items()
        ]
    }

@router.get("/dashboard")
async def get_compliance_dashboard(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get compliance dashboard data."""
    
    engine = ComplianceEngine(db)
    
    # Get assessments for all frameworks
    frameworks = [ComplianceFramework.SOC2, ComplianceFramework.ISO27001, ComplianceFramework.AWSFOUNDATIONAL]
    
    framework_assessments = []
    for framework in frameworks:
        try:
            assessment = await engine._assess_framework(str(organization.id), framework)
            
            framework_assessments.append({
                "framework": framework.value,
                "score": assessment.overall_score,
                "passed": assessment.passed_controls,
                "total": assessment.total_controls,
                "status": "compliant" if assessment.overall_score >= 80 else "non_compliant",
                "last_assessed": assessment.last_assessed.isoformat()
            })
        except Exception as e:
            print(f"Error assessing {framework.value}: {e}")
    
    # Get timeline for primary framework
    timeline = await engine.get_compliance_timeline(
        str(organization.id),
        ComplianceFramework.SOC2,
        days=30
    )
    
    # Get high-risk controls
    recommendations = await engine.get_remediation_recommendations(
        str(organization.id),
        ComplianceFramework.SOC2
    )
    
    high_risk_controls = [
        rec for rec in recommendations[:5] if rec["risk_score"] > 70
    ]
    
    return {
        "summary": {
            "average_score": sum(f["score"] for f in framework_assessments) / len(framework_assessments) if framework_assessments else 0,
            "compliant_frameworks": len([f for f in framework_assessments if f["status"] == "compliant"]),
            "total_frameworks": len(framework_assessments),
            "high_risk_controls": len(high_risk_controls)
        },
        "frameworks": framework_assessments,
        "timeline": timeline,
        "high_risk_controls": high_risk_controls,
        "last_updated": datetime.utcnow().isoformat()
    }

@router.get("/controls")
async def get_compliance_controls(
    framework: Optional[str] = Query(None, description="Filter by framework"),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get compliance controls with filtering."""
    
    engine = ComplianceEngine(db)
    
    if framework:
        try:
            framework_enum = ComplianceFramework(framework)
            assessment = await engine._assess_framework(str(organization.id), framework_enum)
            
            controls = []
            for control_id, control_assessment in assessment.assessments.items():
                # Find control details
                control_details = next(
                    (c for c in engine.frameworks[framework_enum] if c.control_id == control_id),
                    None
                )
                
                if control_details:
                    if status and control_assessment.status.value != status:
                        continue
                    
                    if severity and control_details.severity != severity:
                        continue
                    
                    controls.append({
                        "id": control_id,
                        "title": control_details.title,
                        "description": control_details.description,
                        "framework": framework,
                        "severity": control_details.severity,
                        "status": control_assessment.status.value,
                        "risk_score": control_assessment.risk_score,
                        "automated": control_details.automated,
                        "evidence_count": len(control_assessment.evidence),
                        "last_assessed": control_assessment.last_assessed.isoformat()
                    })
            
            return {
                "framework": framework,
                "controls": controls,
                "count": len(controls)
            }
            
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid framework")
    
    # Return all controls across frameworks (simplified)
    all_controls = []
    for framework_enum, controls in engine.frameworks.items():
        for control in controls[:5]:  # Limit for demo
            all_controls.append({
                "id": control.control_id,
                "title": control.title,
                "framework": framework_enum.value,
                "severity": control.severity,
                "automated": control.automated
            })
    
    return {
        "controls": all_controls,
        "total": len(all_controls)
    }

@router.post("/evidence")
async def collect_evidence(
    request: EvidenceRequest,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Collect evidence for compliance control."""
    
    engine = ComplianceEngine(db)
    
    try:
        framework = ComplianceFramework(request.framework)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid framework")
    
    # Get control details
    control = next(
        (c for c in engine.frameworks.get(framework, []) if c.control_id == request.control_id),
        None
    )
    
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    
    # Get accounts
    from app.models.cloud_account import CloudAccount
    result = await db.execute(
        select(CloudAccount).where(
            and_(
                CloudAccount.organization_id == str(organization.id),
                CloudAccount.is_active == True
            )
        )
    )
    accounts = result.scalars().all()
    
    # Collect evidence
    evidence = await engine._collect_evidence(
        str(organization.id), control, accounts
    )
    
    # Filter by evidence type if specified
    if request.evidence_type:
        evidence = [e for e in evidence if e.get("type") == request.evidence_type]
    
    return {
        "control_id": request.control_id,
        "framework": request.framework,
        "evidence": evidence,
        "count": len(evidence),
        "collected_at": datetime.utcnow().isoformat()
    }

@router.post("/reports/generate")
async def generate_compliance_report(
    framework: str,
    format: str = Query("pdf", description="Report format: pdf, html, json"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Generate compliance report."""
    
    try:
        framework_enum = ComplianceFramework(framework)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid framework")
    
    engine = ComplianceEngine(db)
    
    report = await engine.generate_compliance_report(
        str(organization.id), framework_enum, format
    )
    
    return report

@router.get("/reports")
async def get_compliance_reports(
    framework: Optional[str] = Query(None, description="Filter by framework"),
    limit: int = Query(20, description="Limit results"),
    offset: int = Query(0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get compliance reports."""
    
    from app.models.compliance import ComplianceReport
    from sqlalchemy import select, func
    
    query = select(ComplianceReport).where(
        ComplianceReport.organization_id == str(organization.id)
    )
    
    if framework:
        query = query.where(ComplianceReport.framework == framework)
    
    query = query.order_by(ComplianceReport.generated_at.desc())
    
    result = await db.execute(query.offset(offset).limit(limit))
    reports = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(ComplianceReport).where(
            ComplianceReport.organization_id == str(organization.id)
        )
    )
    total = count_result.scalar()
    
    return {
        "reports": [
            {
                "id": report.id,
                "framework": report.framework,
                "format": report.format,
                "score": report.overall_score,
                "download_url": report.download_url,
                "generated_at": report.generated_at.isoformat(),
                "size_mb": report.size_mb or 0
            }
            for report in reports
        ],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
    }

@router.get("/timeline/{framework}")
async def get_compliance_timeline(
    framework: str,
    days: int = Query(30, description="Number of days"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get compliance score timeline."""
    
    try:
        framework_enum = ComplianceFramework(framework)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid framework")
    
    engine = ComplianceEngine(db)
    timeline = await engine.get_compliance_timeline(
        str(organization.id), framework_enum, days
    )
    
    return {
        "framework": framework,
        "timeline": timeline,
        "current_score": timeline[0]["score"] if timeline else 0,
        "trend": "improving" if timeline and timeline[0]["score"] > timeline[-1]["score"] else "declining"
    }

@router.get("/recommendations")
async def get_compliance_recommendations(
    framework: str,
    priority: Optional[str] = Query(None, description="Filter by priority"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get compliance improvement recommendations."""
    
    try:
        framework_enum = ComplianceFramework(framework)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid framework")
    
    engine = ComplianceEngine(db)
    recommendations = await engine.get_remediation_recommendations(
        str(organization.id), framework_enum
    )
    
    if priority:
        recommendations = [r for r in recommendations if r["priority"] == priority]
    
    return {
        "framework": framework,
        "recommendations": recommendations,
        "high_priority": len([r for r in recommendations if r["priority"] == "high"]),
        "total": len(recommendations)
    }

@router.get("/evidence-library")
async def get_evidence_library(
    control_id: Optional[str] = Query(None, description="Filter by control ID"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get evidence library for compliance."""
    
    from app.models.compliance import ComplianceEvidence
    from sqlalchemy import select, func
    
    query = select(ComplianceEvidence).where(
        ComplianceEvidence.organization_id == str(organization.id)
    )
    
    if control_id:
        query = query.where(ComplianceEvidence.control_id == control_id)
    
    query = query.order_by(ComplianceEvidence.collected_at.desc())
    
    result = await db.execute(query.limit(50))
    evidence_items = result.scalars().all()
    
    return {
        "evidence": [
            {
                "id": ev.id,
                "control_id": ev.control_id,
                "framework": ev.framework,
                "evidence_type": ev.evidence_type,
                "description": ev.description,
                "collected_at": ev.collected_at.isoformat(),
                "automated": ev.automated,
                "size_kb": ev.size_kb or 0
            }
            for ev in evidence_items
        ],
        "total": len(evidence_items),
        "by_type": {
            "configuration": len([e for e in evidence_items if e.evidence_type == "configuration"]),
            "log": len([e for e in evidence_items if e.evidence_type == "log"]),
            "screenshot": len([e for e in evidence_items if e.evidence_type == "screenshot"])
        }
    }