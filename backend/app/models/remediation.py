from app.database import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

class RemediationTask(Base):
    __tablename__ = "remediation_tasks"
    
    id = Column(String, primary_key=True, default=lambda: f"task_{uuid.uuid4()}")
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Action details
    action_id = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    region = Column(String, nullable=False)
    parameters = Column(JSON, default=dict)
    
    # Status and tracking
    status = Column(String, default="pending", index=True)
    requested_by = Column(String, nullable=False)
    requested_at = Column(DateTime, default=func.now(), index=True)
    approved_by = Column(String)
    approved_at = Column(DateTime)
    executed_by = Column(String)
    executed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Execution details
    execution_log = Column(JSON, default=list)
    dry_run = Column(Boolean, default=False)
    rollback_data = Column(JSON)
    error_message = Column(Text)
    
    # Relationships
    approvals = relationship("RemediationApproval", back_populates="task")
    
    __table_args__ = (
        Index('ix_remediation_tasks_org_status', 'organization_id', 'status'),
        Index('ix_remediation_tasks_requested', 'requested_at'),
    )

class RemediationApproval(Base):
    __tablename__ = "remediation_approvals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String, ForeignKey("remediation_tasks.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Approval details
    approver_email = Column(String, nullable=False)
    approver_role = Column(String)
    status = Column(String, default="pending", index=True)  # pending, approved, rejected
    comment = Column(Text)
    requested_at = Column(DateTime, default=func.now())
    responded_at = Column(DateTime)
    
    # Relationships
    task = relationship("RemediationTask", back_populates="approvals")
    
    __table_args__ = (
        Index('ix_remediation_approvals_task_status', 'task_id', 'status'),
    )

class RemediationWorkflow(Base):
    __tablename__ = "remediation_workflows"
    
    id = Column(String, primary_key=True, default=lambda: f"wf_{uuid.uuid4()}")
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Workflow definition
    name = Column(String, nullable=False)
    description = Column(Text)
    trigger_type = Column(String, nullable=False)  # security_finding, cost_anomaly, etc.
    trigger_conditions = Column(JSON, default=dict)
    steps = Column(JSON, default=list)  # List of workflow steps
    
    # Status and versioning
    status = Column(String, default="draft", index=True)  # draft, active, inactive, archived
    version = Column(Integer, default=1)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    executions = relationship("WorkflowExecution", back_populates="workflow")
    
    __table_args__ = (
        Index('ix_remediation_workflows_org_status', 'organization_id', 'status'),
    )

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    
    id = Column(String, primary_key=True, default=lambda: f"exec_{uuid.uuid4()}")
    workflow_id = Column(String, ForeignKey("remediation_workflows.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Execution state
    status = Column(String, default="running", index=True)  # running, completed, failed, paused
    trigger_data = Column(JSON, default=dict)  # Data that triggered the workflow
    current_step_id = Column(String)
    execution_log = Column(JSON, default=list)
    
    # Timestamps
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    workflow = relationship("RemediationWorkflow", back_populates="executions")
    approvals = relationship("WorkflowApproval", back_populates="execution")
    
    __table_args__ = (
        Index('ix_workflow_executions_workflow_status', 'workflow_id', 'status'),
    )

class WorkflowApproval(Base):
    __tablename__ = "workflow_approvals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_execution_id = Column(String, ForeignKey("workflow_executions.id"), nullable=False)
    step_id = Column(String, nullable=False)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Approval details
    approvers = Column(JSON, default=list)  # List of approver emails/roles
    status = Column(String, default="pending", index=True)  # pending, approved, rejected
    approved_by = Column(String)
    approved_at = Column(DateTime)
    comment = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)  # When this approval expires
    
    # Relationships
    execution = relationship("WorkflowExecution", back_populates="approvals")
    
    __table_args__ = (
        Index('ix_workflow_approvals_execution_step', 'workflow_execution_id', 'step_id'),
    )