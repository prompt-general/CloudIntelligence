from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import json
import yaml
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
import asyncio

class ComplianceFramework(Enum):
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    HIPAA = "hipaa"
    PCIDSS = "pcidss"
    GDPR = "gdpr"
    AWSNIST = "aws_nist"
    AWSFOUNDATIONAL = "aws_foundational"

class ControlStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
    NOT_ASSESSED = "not_assessed"

class EvidenceType(Enum):
    CONFIGURATION = "configuration"
    LOG = "log"
    SCREENSHOT = "screenshot"
    DOCUMENT = "document"
    API_RESPONSE = "api_response"

@dataclass
class ComplianceControl:
    id: str
    framework: ComplianceFramework
    control_id: str
    title: str
    description: str
    requirements: List[str]
    resource_types: List[str]
    severity: str
    automated: bool
    evidence_requirements: List[Dict[str, Any]]

@dataclass
class ControlAssessment:
    control_id: str
    status: ControlStatus
    evidence: List[Dict[str, Any]]
    last_assessed: datetime
    failure_reasons: List[str]
    risk_score: float
    automated: bool

@dataclass
class FrameworkAssessment:
    framework: ComplianceFramework
    organization_id: str
    assessments: Dict[str, ControlAssessment]
    overall_score: float
    passed_controls: int
    total_controls: int
    last_assessed: datetime
    next_assessment_due: datetime

class ComplianceEngine:
    """AI-powered compliance automation and evidence collection engine."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.frameworks = self._load_compliance_frameworks()
        self.evidence_collectors = self._initialize_evidence_collectors()
    
    async def assess_organization(
        self,
        organization_id: str,
        frameworks: Optional[List[str]] = None
    ) -> Dict[str, FrameworkAssessment]:
        """Run comprehensive compliance assessment for organization."""
        
        if frameworks is None:
            frameworks = [f.value for f in ComplianceFramework]
        
        results = {}
        
        for framework_str in frameworks:
            try:
                framework = ComplianceFramework(framework_str)
                assessment = await self._assess_framework(
                    organization_id, framework
                )
                results[framework.value] = assessment
            except ValueError:
                continue
        
        return results
    
    async def _assess_framework(
        self,
        organization_id: str,
        framework: ComplianceFramework
    ) -> FrameworkAssessment:
        """Assess compliance for a specific framework."""
        
        # Get controls for framework
        controls = self.frameworks.get(framework, [])
        
        # Get cloud accounts for organization
        from app.models.cloud_account import CloudAccount
        result = await self.db.execute(
            select(CloudAccount).where(
                and_(
                    CloudAccount.organization_id == organization_id,
                    CloudAccount.is_active == True
                )
            )
        )
        accounts = result.scalars().all()
        
        assessments = {}
        passed_count = 0
        
        # Assess each control
        for control in controls[:10]:  # Limit for demo
            assessment = await self._assess_control(
                organization_id, control, accounts
            )
            assessments[control.control_id] = assessment
            
            if assessment.status == ControlStatus.PASSED:
                passed_count += 1
        
        total_controls = len(assessments)
        overall_score = (passed_count / total_controls * 100) if total_controls > 0 else 100
        
        return FrameworkAssessment(
            framework=framework,
            organization_id=organization_id,
            assessments=assessments,
            overall_score=overall_score,
            passed_controls=passed_count,
            total_controls=total_controls,
            last_assessed=datetime.utcnow(),
            next_assessment_due=datetime.utcnow() + timedelta(days=7)
        )
    
    async def _assess_control(
        self,
        organization_id: str,
        control: ComplianceControl,
        accounts: List[Any]
    ) -> ControlAssessment:
        """Assess a single compliance control."""
        
        evidence = []
        failure_reasons = []
        
        # Try automated assessment first
        if control.automated:
            assessment_result = await self._automated_assessment(
                organization_id, control, accounts
            )
            
            if assessment_result["status"] == "passed":
                evidence.extend(assessment_result.get("evidence", []))
            else:
                failure_reasons.extend(assessment_result.get("failure_reasons", []))
                # Mark for manual review
                return ControlAssessment(
                    control_id=control.control_id,
                    status=ControlStatus.FAILED,
                    evidence=evidence,
                    last_assessed=datetime.utcnow(),
                    failure_reasons=failure_reasons,
                    risk_score=80.0,
                    automated=True
                )
        
        # Collect evidence
        evidence_collected = await self._collect_evidence(
            organization_id, control, accounts
        )
        evidence.extend(evidence_collected)
        
        # Determine status based on evidence
        status = self._determine_control_status(evidence, failure_reasons)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(control, status, failure_reasons)
        
        return ControlAssessment(
            control_id=control.control_id,
            status=status,
            evidence=evidence,
            last_assessed=datetime.utcnow(),
            failure_reasons=failure_reasons,
            risk_score=risk_score,
            automated=control.automated
        )
    
    async def _automated_assessment(
        self,
        organization_id: str,
        control: ComplianceControl,
        accounts: List[Any]
    ) -> Dict[str, Any]:
        """Perform automated compliance check."""
        
        # Map control IDs to specific checks
        control_checks = {
            # SOC2 Controls
            "CC6.1": self._check_logging_enabled,
            "CC6.6": self._check_configuration_management,
            "CC6.7": self._check_vulnerability_management,
            
            # ISO27001 Controls
            "A.12.4.1": self._check_event_logging,
            "A.13.1.1": self._check_network_security,
            "A.14.1.2": self._check_security_requirements,
            
            # AWS Foundational
            "IAM.1": self._check_iam_mfa,
            "S3.1": self._check_s3_public_access,
            "EC2.1": self._check_ec2_security_groups,
        }
        
        check_function = control_checks.get(control.control_id)
        if check_function:
            return await check_function(organization_id, accounts)
        
        return {"status": "not_automated", "evidence": []}
    
    async def _check_logging_enabled(
        self, organization_id: str, accounts: List[Any]
    ) -> Dict[str, Any]:
        """SOC2 CC6.1: Logging should be enabled."""
        evidence = []
        failure_reasons = []
        
        for account in accounts:
            if account.provider == "aws":
                # Check CloudTrail
                try:
                    from app.services.aws.client import AWSClient
                    aws_client = AWSClient()
                    session = await aws_client.get_session(
                        account.role_arn,
                        account.external_id,
                        account.regions[0] if account.regions else "us-east-1"
                    )
                    
                    def _check_cloudtrail():
                        cloudtrail = session.client('cloudtrail')
                        trails = cloudtrail.describe_trails()['trailList']
                        
                        multi_region_active = False
                        for trail in trails:
                            if trail.get('IsMultiRegionTrail', False):
                                status = cloudtrail.get_trail_status(Name=trail['TrailARN'])
                                if status.get('IsLogging', False):
                                    multi_region_active = True
                                    evidence.append({
                                        "type": "api_response",
                                        "data": {
                                            "trail_name": trail['Name'],
                                            "trail_arn": trail['TrailARN'],
                                            "is_logging": True,
                                            "is_multi_region": True
                                        },
                                        "timestamp": datetime.utcnow().isoformat()
                                    })
                        
                        return multi_region_active
                    
                    loop = asyncio.get_event_loop()
                    has_logging = await loop.run_in_executor(None, _check_cloudtrail)
                    
                    if not has_logging:
                        failure_reasons.append(f"No active multi-region CloudTrail trail in account {account.account_id}")
                    
                except Exception as e:
                    failure_reasons.append(f"Error checking CloudTrail: {str(e)}")
        
        if failure_reasons:
            return {
                "status": "failed",
                "failure_reasons": failure_reasons,
                "evidence": evidence
            }
        
        return {
            "status": "passed",
            "evidence": evidence
        }
    
    async def _check_iam_mfa(
        self, organization_id: str, accounts: List[Any]
    ) -> Dict[str, Any]:
        """AWS Foundational IAM.1: IAM users should have MFA enabled."""
        evidence = []
        failure_reasons = []
        
        for account in accounts:
            if account.provider == "aws":
                try:
                    from app.services.aws.client import AWSClient
                    aws_client = AWSClient()
                    session = await aws_client.get_session(
                        account.role_arn,
                        account.external_id,
                        account.regions[0] if account.regions else "us-east-1"
                    )
                    
                    def _check_iam_mfa():
                        iam = session.client('iam')
                        users = iam.list_users()['Users']
                        
                        users_without_mfa = []
                        for user in users:
                            mfa_devices = iam.list_mfa_devices(UserName=user['UserName'])['MFADevices']
                            if not mfa_devices:
                                users_without_mfa.append(user['UserName'])
                        
                        return users_without_mfa
                    
                    loop = asyncio.get_event_loop()
                    users_without_mfa = await loop.run_in_executor(None, _check_iam_mfa)
                    
                    if users_without_mfa:
                        failure_reasons.append(
                            f"Account {account.account_id} has {len(users_without_mfa)} users without MFA: {', '.join(users_without_mfa[:5])}"
                        )
                    
                    evidence.append({
                        "type": "api_response",
                        "data": {
                            "account_id": account.account_id,
                            "users_without_mfa_count": len(users_without_mfa),
                            "users_without_mfa": users_without_mfa[:10],
                            "total_users": len(users_without_mfa)
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    failure_reasons.append(f"Error checking IAM MFA: {str(e)}")
        
        if failure_reasons:
            return {
                "status": "failed",
                "failure_reasons": failure_reasons,
                "evidence": evidence
            }
        
        return {
            "status": "passed",
            "evidence": evidence
        }
    
    async def _collect_evidence(
        self,
        organization_id: str,
        control: ComplianceControl,
        accounts: List[Any]
    ) -> List[Dict[str, Any]]:
        """Collect evidence for compliance control."""
        evidence = []
        
        # Collect evidence based on requirements
        for evidence_req in control.evidence_requirements:
            evidence_type = evidence_req.get("type", "configuration")
            
            if evidence_type == "configuration":
                config_evidence = await self._collect_configuration_evidence(
                    organization_id, control, accounts, evidence_req
                )
                evidence.extend(config_evidence)
            
            elif evidence_type == "log":
                log_evidence = await self._collect_log_evidence(
                    organization_id, control, accounts, evidence_req
                )
                evidence.extend(log_evidence)
        
        return evidence
    
    async def _collect_configuration_evidence(
        self,
        organization_id: str,
        control: ComplianceControl,
        accounts: List[Any],
        requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Collect configuration evidence."""
        evidence = []
        
        # This would collect specific configuration evidence
        # For now, return sample evidence
        evidence.append({
            "type": "configuration",
            "control_id": control.control_id,
            "resource_type": requirements.get("resource_type", "general"),
            "configuration": {
                "enabled": True,
                "version": "1.0",
                "last_modified": datetime.utcnow().isoformat()
            },
            "collected_at": datetime.utcnow().isoformat(),
            "automated": True
        })
        
        return evidence
    
    async def _collect_log_evidence(
        self,
        organization_id: str,
        control: ComplianceControl,
        accounts: List[Any],
        requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Collect log evidence."""
        evidence = []
        
        # Sample log evidence
        evidence.append({
            "type": "log",
            "control_id": control.control_id,
            "log_type": requirements.get("log_type", "audit"),
            "entries": [
                {
                    "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                    "event": "Configuration change",
                    "user": "system",
                    "resource": "s3-bucket",
                    "action": "modify"
                }
            ],
            "collected_at": datetime.utcnow().isoformat(),
            "automated": True
        })
        
        return evidence
    
    def _determine_control_status(
        self,
        evidence: List[Dict[str, Any]],
        failure_reasons: List[str]
    ) -> ControlStatus:
        """Determine control status based on evidence and failures."""
        if failure_reasons:
            return ControlStatus.FAILED
        
        if not evidence:
            return ControlStatus.NOT_ASSESSED
        
        # Check evidence for compliance indicators
        for ev in evidence:
            if ev.get("type") == "configuration":
                config = ev.get("configuration", {})
                if not config.get("enabled", True):
                    return ControlStatus.FAILED
        
        return ControlStatus.PASSED
    
    def _calculate_risk_score(
        self,
        control: ComplianceControl,
        status: ControlStatus,
        failure_reasons: List[str]
    ) -> float:
        """Calculate risk score for control."""
        base_scores = {
            ControlStatus.PASSED: 0,
            ControlStatus.FAILED: 80,
            ControlStatus.NOT_ASSESSED: 40,
            ControlStatus.NOT_APPLICABLE: 0
        }
        
        base_score = base_scores.get(status, 50)
        
        # Adjust based on severity
        severity_weights = {
            "critical": 1.3,
            "high": 1.2,
            "medium": 1.0,
            "low": 0.8
        }
        
        weight = severity_weights.get(control.severity, 1.0)
        
        # Adjust for number of failures
        if failure_reasons:
            base_score += len(failure_reasons) * 5
        
        return min(100, base_score * weight)
    
    def _load_compliance_frameworks(self) -> Dict[ComplianceFramework, List[ComplianceControl]]:
        """Load compliance frameworks and controls."""
        frameworks = {}
        
        # SOC2 Controls
        soc2_controls = [
            ComplianceControl(
                id="soc2_cc6_1",
                framework=ComplianceFramework.SOC2,
                control_id="CC6.1",
                title="Logical and Physical Access Controls",
                description="The entity implements logical and physical access controls to protect against unauthorized access.",
                requirements=[
                    "Implement multi-factor authentication",
                    "Maintain access logs",
                    "Regular access reviews"
                ],
                resource_types=["AWS::IAM::User", "AWS::IAM::Role"],
                severity="high",
                automated=True,
                evidence_requirements=[
                    {
                        "type": "configuration",
                        "resource_type": "IAM",
                        "requirements": ["MFA enabled", "Access logging"]
                    }
                ]
            ),
            ComplianceControl(
                id="soc2_cc6_6",
                framework=ComplianceFramework.SOC2,
                control_id="CC6.6",
                title="Logical Access Security Software",
                description="The entity implements logical access security software to protect information assets.",
                requirements=[
                    "Network security groups",
                    "Firewall configurations",
                    "Intrusion detection"
                ],
                resource_types=["AWS::EC2::SecurityGroup", "AWS::VPC"],
                severity="high",
                automated=True,
                evidence_requirements=[]
            )
        ]
        frameworks[ComplianceFramework.SOC2] = soc2_controls
        
        # ISO27001 Controls
        iso27001_controls = [
            ComplianceControl(
                id="iso27001_a12_4_1",
                framework=ComplianceFramework.ISO27001,
                control_id="A.12.4.1",
                title="Event Logging",
                description="Event logs recording user activities, exceptions, and security events should be produced and retained.",
                requirements=[
                    "Enable CloudTrail logging",
                    "Retain logs for 90+ days",
                    "Monitor log integrity"
                ],
                resource_types=["AWS::CloudTrail::Trail"],
                severity="medium",
                automated=True,
                evidence_requirements=[]
            )
        ]
        frameworks[ComplianceFramework.ISO27001] = iso27001_controls
        
        # AWS Foundational Controls
        aws_controls = [
            ComplianceControl(
                id="aws_foundational_iam_1",
                framework=ComplianceFramework.AWSFOUNDATIONAL,
                control_id="IAM.1",
                title="IAM Root User Hardening",
                description="Ensure multi-factor authentication (MFA) is enabled for all IAM users with console password.",
                requirements=[
                    "MFA enabled for all IAM users",
                    "No access keys for root user",
                    "Strong password policy"
                ],
                resource_types=["AWS::IAM::User"],
                severity="critical",
                automated=True,
                evidence_requirements=[]
            ),
            ComplianceControl(
                id="aws_foundational_s3_1",
                framework=ComplianceFramework.AWSFOUNDATIONAL,
                control_id="S3.1",
                title="S3 Block Public Access",
                description="Ensure S3 buckets do not allow public access.",
                requirements=[
                    "Block public ACLs",
                    "Block public bucket policies",
                    "Restrict public buckets"
                ],
                resource_types=["AWS::S3::Bucket"],
                severity="critical",
                automated=True,
                evidence_requirements=[]
            )
        ]
        frameworks[ComplianceFramework.AWSFOUNDATIONAL] = aws_controls
        
        return frameworks
    
    def _initialize_evidence_collectors(self) -> Dict[str, Any]:
        """Initialize evidence collection modules."""
        return {
            "aws": self._collect_aws_evidence,
            "azure": self._collect_azure_evidence,
            "gcp": self._collect_gcp_evidence
        }
    
    async def _collect_aws_evidence(
        self,
        account: Any,
        control: ComplianceControl
    ) -> List[Dict[str, Any]]:
        """Collect evidence from AWS."""
        evidence = []
        
        try:
            from app.services.aws.client import AWSClient
            aws_client = AWSClient()
            session = await aws_client.get_session(
                account.role_arn,
                account.external_id,
                account.regions[0] if account.regions else "us-east-1"
            )
            
            # Collect evidence based on control requirements
            # This is a simplified implementation
            
            evidence.append({
                "type": "api_response",
                "provider": "aws",
                "account_id": account.account_id,
                "collected_at": datetime.utcnow().isoformat(),
                "data": {
                    "control": control.control_id,
                    "status": "collected"
                }
            })
            
        except Exception as e:
            print(f"Error collecting AWS evidence: {e}")
        
        return evidence
    
    async def _collect_azure_evidence(
        self,
        account: Any,
        control: ComplianceControl
    ) -> List[Dict[str, Any]]:
        """Collect evidence from Azure."""
        # Placeholder for Azure evidence collection
        return []
    
    async def _collect_gcp_evidence(
        self,
        account: Any,
        control: ComplianceControl
    ) -> List[Dict[str, Any]]:
        """Collect evidence from GCP."""
        # Placeholder for GCP evidence collection
        return []
    
    async def generate_compliance_report(
        self,
        organization_id: str,
        framework: ComplianceFramework,
        format: str = "pdf"
    ) -> Dict[str, Any]:
        """Generate compliance assessment report."""
        
        assessment = await self._assess_framework(organization_id, framework)
        
        # Get organization details
        from app.models.organization import Organization
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        organization = result.scalar_one_or_none()
        
        report_data = {
            "organization": {
                "id": organization.id if organization else organization_id,
                "name": organization.name if organization else "Unknown",
                "assessment_date": datetime.utcnow().isoformat()
            },
            "framework": framework.value,
            "assessment": {
                "overall_score": assessment.overall_score,
                "passed_controls": assessment.passed_controls,
                "total_controls": assessment.total_controls,
                "last_assessed": assessment.last_assessed.isoformat()
            },
            "controls": []
        }
        
        for control_id, control_assessment in assessment.assessments.items():
            # Find control details
            control_details = next(
                (c for c in self.frameworks[framework] if c.control_id == control_id),
                None
            )
            
            report_data["controls"].append({
                "control_id": control_id,
                "title": control_details.title if control_details else control_id,
                "description": control_details.description if control_details else "",
                "status": control_assessment.status.value,
                "risk_score": control_assessment.risk_score,
                "automated": control_assessment.automated,
                "evidence_count": len(control_assessment.evidence),
                "failure_reasons": control_assessment.failure_reasons,
                "last_assessed": control_assessment.last_assessed.isoformat()
            })
        
        # Sort controls by risk score (highest first)
        report_data["controls"].sort(key=lambda x: x["risk_score"], reverse=True)
        
        # Generate report in requested format
        if format == "pdf":
            report_url = await self._generate_pdf_report(report_data)
        elif format == "json":
            report_url = await self._generate_json_report(report_data)
        else:
            report_url = await self._generate_html_report(report_data)
        
        return {
            "report_id": f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "framework": framework.value,
            "format": format,
            "download_url": report_url,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "score": assessment.overall_score,
                "status": "compliant" if assessment.overall_score >= 80 else "non_compliant",
                "high_risk_controls": len([c for c in report_data["controls"] if c["risk_score"] > 70])
            }
        }
    
    async def _generate_pdf_report(self, report_data: Dict[str, Any]) -> str:
        """Generate PDF compliance report."""
        # This would use a PDF generation library like ReportLab
        # For now, return a mock URL
        return f"/reports/{report_data['framework']}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    
    async def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML compliance report."""
        # Generate HTML report
        return f"/reports/{report_data['framework']}_{datetime.utcnow().strftime('%Y%m%d')}.html"
    
    async def _generate_json_report(self, report_data: Dict[str, Any]) -> str:
        """Generate JSON compliance report."""
        # Generate JSON report
        return f"/reports/{report_data['framework']}_{datetime.utcnow().strftime('%Y%m%d')}.json"
    
    async def get_compliance_timeline(
        self,
        organization_id: str,
        framework: ComplianceFramework,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get compliance score timeline."""
        
        # This would query historical assessment data
        # For now, generate mock timeline data
        
        timeline = []
        end_date = datetime.utcnow()
        
        for i in range(days):
            date = end_date - timedelta(days=i)
            score = 85 - (i % 10) + (i % 3)  # Mock varying scores
            
            timeline.append({
                "date": date.date().isoformat(),
                "score": score,
                "status": "compliant" if score >= 80 else "non_compliant",
                "assessments": 1,
                "failed_controls": max(0, int((100 - score) / 10))
            })
        
        return sorted(timeline, key=lambda x: x["date"])
    
    async def get_remediation_recommendations(
        self,
        organization_id: str,
        framework: ComplianceFramework
    ) -> List[Dict[str, Any]]:
        """Get recommendations for improving compliance."""
        
        assessment = await self._assess_framework(organization_id, framework)
        
        recommendations = []
        
        for control_id, control_assessment in assessment.assessments.items():
            if control_assessment.status == ControlStatus.FAILED:
                # Find control details
                control_details = next(
                    (c for c in self.frameworks[framework] if c.control_id == control_id),
                    None
                )
                
                if control_details:
                    recommendations.append({
                        "control_id": control_id,
                        "title": control_details.title,
                        "description": control_details.description,
                        "risk_score": control_assessment.risk_score,
                        "failure_reasons": control_assessment.failure_reasons,
                        "recommended_actions": self._generate_remediation_actions(control_details),
                        "estimated_effort": "low" if control_details.automated else "medium",
                        "priority": "high" if control_assessment.risk_score > 70 else "medium"
                    })
        
        # Sort by risk score (highest first)
        recommendations.sort(key=lambda x: x["risk_score"], reverse=True)
        
        return recommendations
    
    def _generate_remediation_actions(self, control: ComplianceControl) -> List[str]:
        """Generate remediation actions for failed control."""
        
        actions_map = {
            "IAM.1": [
                "Enable MFA for all IAM users",
                "Implement IAM password policy",
                "Disable root user access keys"
            ],
            "S3.1": [
                "Enable S3 Block Public Access",
                "Review and update bucket policies",
                "Enable S3 access logging"
            ],
            "CC6.1": [
                "Enable CloudTrail in all regions",
                "Enable CloudTrail log file validation",
                "Configure CloudTrail to send logs to S3"
            ]
        }
        
        return actions_map.get(control.control_id, [
            f"Review and fix {control.control_id} compliance requirements",
            "Consult security team for guidance"
        ])