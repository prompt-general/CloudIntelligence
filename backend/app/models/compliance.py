from app.database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

class ComplianceFramework(Base):
    __tablename__ = "compliance_frameworks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Framework details
    name = Column(String(100), nullable=False)
    description = Column(Text)
    version = Column(String(50))
    standard = Column(String(100))  # SOC2, ISO27001, etc.
    
    # Status
    is_active = Column(Boolean, default=True)
    last_assessed = Column(DateTime)
    next_assessment_due = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    assessments = relationship("ComplianceAssessment", back_populates="framework")
    controls = relationship("ComplianceControl", back_populates="framework")

class ComplianceControl(Base):
    __tablename__ = "compliance_controls"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    framework_id = Column(UUID(as_uuid=True), ForeignKey("compliance_frameworks.id"), nullable=False)
    
    # Control details
    control_id = Column(String(50), nullable=False)  # CC6.1, A.12.4.1, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text)
    requirements = Column(JSON)  # List of requirements
    severity = Column(String(20))  # critical, high, medium, low
    category = Column(String(100))  # access, logging, encryption, etc.
    
    # Automation
    is_automated = Column(Boolean, default=False)
    check_type = Column(String(50))  # aws_config, custom_check, manual
    
    # Evidence requirements
    evidence_requirements = Column(JSON)
    
    # Relationships
    framework = relationship("ComplianceFramework", back_populates="controls")
    assessments = relationship("ControlAssessment", back_populates="control")
    evidence = relationship("ComplianceEvidence", back_populates="control")

class ComplianceAssessment(Base):
    __tablename__ = "compliance_assessments"
    
    id = Column(String(50), primary_key=True)  # assessment_{timestamp}
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    framework_id = Column(UUID(as_uuid=True), ForeignKey("compliance_frameworks.id"), nullable=False)
    
    # Assessment results
    overall_score = Column(Float, nullable=False)
    passed_controls = Column(Integer, default=0)
    failed_controls = Column(Integer, default=0)
    not_assessed_controls = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default="completed")  # in_progress, completed, failed
    assessed_by = Column(String(200))  # User or system
    assessed_at = Column(DateTime, default=func.now())
    
    # Raw data
    assessment_data = Column(JSON)  # Full assessment results
    
    # Relationships
    framework = relationship("ComplianceFramework", back_populates="assessments")
    control_assessments = relationship("ControlAssessment", back_populates="assessment")

class ControlAssessment(Base):
    __tablename__ = "control_assessments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(String(50), ForeignKey("compliance_assessments.id"), nullable=False)
    control_id = Column(UUID(as_uuid=True), ForeignKey("compliance_controls.id"), nullable=False)
    
    # Assessment details
    status = Column(String(20), nullable=False)  # passed, failed, not_applicable, not_assessed
    risk_score = Column(Float)
    failure_reasons = Column(JSON)  # List of failure reasons
    automated = Column(Boolean, default=False)
    
    # Evidence
    evidence_ids = Column(JSON)  # References to evidence
    
    # Timestamps
    assessed_at = Column(DateTime, default=func.now())
    
    # Relationships
    assessment = relationship("ComplianceAssessment", back_populates="control_assessments")
    control = relationship("ComplianceControl", back_populates="assessments")

class ComplianceEvidence(Base):
    __tablename__ = "compliance_evidence"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    control_id = Column(UUID(as_uuid=True), ForeignKey("compliance_controls.id"), nullable=False)
    
    # Evidence details
    evidence_type = Column(String(50), nullable=False)  # configuration, log, screenshot, document
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Storage
    storage_type = Column(String(20), default="database")  # database, s3, external
    storage_path = Column(String(500))  # URL or path to evidence
    content = Column(Text)  # For small evidence items stored directly
    
    # Metadata
    collected_by = Column(String(200))  # User or system
    collected_at = Column(DateTime, default=func.now())
    automated = Column(Boolean, default=False)
    
    # Audit trail
    source = Column(String(100))  # AWS Config, CloudTrail, manual upload
    checksum = Column(String(100))  # For integrity verification
    
    # Relationships
    control = relationship("ComplianceControl", back_populates="evidence")

class ComplianceReport(Base):
    __tablename__ = "compliance_reports"
    
    id = Column(String(50), primary_key=True)  # report_{timestamp}
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Report details
    framework = Column(String(50), nullable=False)
    report_type = Column(String(50), default="assessment")  # assessment, audit, interim
    format = Column(String(20), default="pdf")  # pdf, html, json
    
    # Results
    overall_score = Column(Float)
    download_url = Column(String(500))
    size_mb = Column(Float)
    
    # Metadata
    generated_by = Column(String(200))
    generated_at = Column(DateTime, default=func.now())
    valid_until = Column(DateTime)  # Report validity
    
    # Audit trail
    version = Column(String(20), default="1.0")
    notes = Column(Text)

class AuditTrail(Base):
    __tablename__ = "compliance_audit_trails"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Audit details
    action = Column(String(100), nullable=False)  # assessment_started, control_updated, evidence_added
    resource_type = Column(String(50))  # assessment, control, evidence
    resource_id = Column(String(100))
    
    # User/System info
    actor = Column(String(200), nullable=False)  # User email or system
    actor_type = Column(String(20), default="user")  # user, system
    
    # Changes
    changes = Column(JSON)  # What changed
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    
    # Timestamp
    created_at = Column(DateTime, default=func.now(), index=True)