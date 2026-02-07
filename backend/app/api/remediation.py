from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.services.remediation.engine import RemediationEngine, RemediationAction, RemediationStatus
from app.services.remediation.workflow import WorkflowManager, WorkflowTriggerType
from app.services.security.scanner import SecurityScanner
from app.services.cost.analyzer import CostAnalyzer
from pydantic import BaseModel

router = APIRouter(prefix="/remediation", tags=["remediation"])

class RemediationRequest(BaseModel):
    finding_id: str
    action_type: str
    parameters: Optional[Dict[str, Any]] = None
    dry_run: bool = True

class WorkflowCreateRequest(BaseModel):
    name: str
    description: str
    trigger_type: str
    trigger_conditions: Dict[str, Any]
    steps: List[Dict[str, Any]]

class WorkflowApprovalRequest(BaseModel):
    comment: Optional[str] = None

@router.get("/actions")
async def get_remediation_actions(
    finding_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get available remediation actions."""
    
    engine = RemediationEngine(db)
    
    if finding_id:
        # Get actions for specific finding
        # This would fetch the finding and generate actions
        pass
    
    # Return action templates
    return {
        "actions": [
            {
                "id": action_id,
                "name": template["name"],
                "description": template["description"],
                "supported_resources": template["supported_resources"],
                "risk_level": template["risk_level"],
                "approval_required": template["approval_required"],
                "execution_time": template["execution_time"]
            }
            for action_id, template in engine.action_templates.items()
        ]
    }

@router.post("/execute")
async def execute_remediation(
    request: RemediationRequest,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Execute a remediation action."""
    
    engine = RemediationEngine(db)
    
    # Create remediation action
    # In production, this would come from a real finding
    action = RemediationAction(
        id=f"action_{uuid.uuid4()}",
        title="Test Remediation",
        description="Test remediation action",
        resource_type="AWS::S3::Bucket",
        resource_id="arn:aws:s3:::test-bucket",
        account_id="123456789012",
        region="us-east-1",
        action_type=request.action_type,
        parameters=request.parameters or {},
        estimated_impact={
            "security_improvement": 30,
            "cost_savings": 100
        },
        risk_level="medium",
        approval_required=False
    )
    
    # Execute remediation
    result = await engine.execute_remediation(
        action=action,
        executed_by=current_user.email,
        dry_run=request.dry_run
    )
    
    # Save to database
    from app.models.remediation import RemediationTask as RemediationTaskModel
    
    task = RemediationTaskModel(
        id=f"task_{uuid.uuid4()}",
        organization_id=str(organization.id),
        action_id=action.id,
        action_type=action.action_type,
        resource_id=action.resource_id,
        resource_type=action.resource_type,
        account_id=action.account_id,
        region=action.region,
        parameters=json.dumps(action.parameters),
        status="completed" if result["success"] else "failed",
        requested_by=current_user.email,
        requested_at=datetime.utcnow(),
        executed_at=datetime.utcnow(),
        execution_log=json.dumps(result.get("execution_log", [])),
        dry_run=request.dry_run,
        rollback_data=json.dumps(result.get("rollback_data", {}))
    )
    
    db.add(task)
    await db.commit()
    
    return {
        "success": result["success"],
        "dry_run": request.dry_run,
        "task_id": task.id,
        "execution_log": result.get("execution_log", []),
        "estimated_impact": action.estimated_impact
    }

@router.get("/tasks")
async def get_remediation_tasks(
    status: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get remediation tasks."""
    
    from app.models.remediation import RemediationTask as RemediationTaskModel
    from sqlalchemy import select, func
    
    query = select(RemediationTaskModel).where(
        RemediationTaskModel.organization_id == str(organization.id)
    )
    
    if status:
        query = query.where(RemediationTaskModel.status == status)
    
    if resource_type:
        query = query.where(RemediationTaskModel.resource_type == resource_type)
    
    query = query.order_by(RemediationTaskModel.requested_at.desc())
    
    result = await db.execute(query.offset(offset).limit(limit))
    tasks = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(RemediationTaskModel).where(
            RemediationTaskModel.organization_id == str(organization.id)
        )
    )
    total = count_result.scalar()
    
    return {
        "tasks": [
            {
                "id": task.id,
                "action_type": task.action_type,
                "resource_id": task.resource_id,
                "resource_type": task.resource_type,
                "account_id": task.account_id,
                "region": task.region,
                "status": task.status,
                "requested_by": task.requested_by,
                "requested_at": task.requested_at.isoformat(),
                "executed_at": task.executed_at.isoformat() if task.executed_at else None,
                "dry_run": task.dry_run,
                "execution_log": json.loads(task.execution_log or '[]') if task.execution_log else []
            }
            for task in tasks
        ],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
    }

@router.post("/workflows")
async def create_workflow(
    request: WorkflowCreateRequest,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Create a remediation workflow."""
    
    manager = WorkflowManager(db)
    
    try:
        workflow = await manager.create_workflow(
            organization_id=str(organization.id),
            name=request.name,
            description=request.description,
            trigger_type=request.trigger_type,
            trigger_conditions=request.trigger_conditions,
            steps=request.steps,
            created_by=current_user.email
        )
        
        return {
            "workflow_id": workflow.id,
            "name": workflow.name,
            "status": workflow.status.value,
            "message": "Workflow created successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/workflows")
async def get_workflows(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get remediation workflows."""
    
    from app.models.remediation import RemediationWorkflow
    from sqlalchemy import select
    
    query = select(RemediationWorkflow).where(
        RemediationWorkflow.organization_id == str(organization.id)
    )
    
    if status:
        query = query.where(RemediationWorkflow.status == status)
    
    query = query.order_by(RemediationWorkflow.created_at.desc())
    
    result = await db.execute(query)
    workflows = result.scalars().all()
    
    return {
        "workflows": [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "trigger_type": wf.trigger_type,
                "status": wf.status,
                "created_by": wf.created_by,
                "created_at": wf.created_at.isoformat(),
                "version": wf.version
            }
            for wf in workflows
        ]
    }

@router.post("/workflows/{workflow_id}/activate")
async def activate_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Activate a workflow."""
    
    from app.models.remediation import RemediationWorkflow
    from sqlalchemy import update
    
    result = await db.execute(
        select(RemediationWorkflow).where(
            and_(
                RemediationWorkflow.id == workflow_id,
                RemediationWorkflow.organization_id == str(organization.id)
            )
        )
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow.status = "active"
    workflow.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "workflow_id": workflow_id,
        "status": "active",
        "message": "Workflow activated"
    }

@router.get("/executions")
async def get_workflow_executions(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get workflow executions."""
    
    from app.models.remediation import WorkflowExecution
    from sqlalchemy import select, func
    
    query = select(WorkflowExecution).where(
        WorkflowExecution.organization_id == str(organization.id)
    )
    
    if workflow_id:
        query = query.where(WorkflowExecution.workflow_id == workflow_id)
    
    if status:
        query = query.where(WorkflowExecution.status == status)
    
    query = query.order_by(WorkflowExecution.started_at.desc())
    
    result = await db.execute(query.offset(offset).limit(limit))
    executions = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(WorkflowExecution).where(
            WorkflowExecution.organization_id == str(organization.id)
        )
    )
    total = count_result.scalar()
    
    return {
        "executions": [
            {
                "id": exec.id,
                "workflow_id": exec.workflow_id,
                "status": exec.status,
                "current_step": exec.current_step_id,
                "started_at": exec.started_at.isoformat(),
                "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                "execution_log": json.loads(exec.execution_log or '[]')
            }
            for exec in executions
        ],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
    }

@router.post("/approvals/{approval_id}/approve")
async def approve_workflow_step(
    approval_id: str,
    request: WorkflowApprovalRequest,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Approve a workflow step."""
    
    from app.models.remediation import WorkflowApproval
    
    result = await db.execute(
        select(WorkflowApproval).where(
            and_(
                WorkflowApproval.id == approval_id,
                WorkflowApproval.status == "pending"
            )
        )
    )
    approval = result.scalar_one_or_none()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found or already processed")
    
    # Check if user is authorized to approve
    approvers = json.loads(approval.approvers or '[]')
    if current_user.email not in approvers:
        raise HTTPException(status_code=403, detail="Not authorized to approve")
    
    approval.status = "approved"
    approval.approved_by = current_user.email
    approval.approved_at = datetime.utcnow()
    approval.comment = request.comment
    
    await db.commit()
    
    # Trigger next step
    manager = WorkflowManager(db)
    await manager.approve_workflow_step(
        execution_id=approval.workflow_execution_id,
        step_id=approval.step_id,
        approver=current_user.email,
        comment=request.comment
    )
    
    return {
        "approval_id": approval_id,
        "status": "approved",
        "approved_by": current_user.email,
        "message": "Step approved successfully"
    }

@router.get("/dashboard")
async def get_remediation_dashboard(
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """Get remediation dashboard data."""
    
    from app.models.remediation import RemediationTask, WorkflowExecution
    from sqlalchemy import select, func
    
    # Get task statistics
    task_result = await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((RemediationTask.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((RemediationTask.status == "failed", 1), else_=0)).label("failed"),
            func.sum(case((RemediationTask.status == "pending", 1), else_=0)).label("pending")
        ).where(
            RemediationTask.organization_id == str(organization.id)
        )
    )
    task_stats = task_result.first()
    
    # Get cost savings
    # This would calculate actual savings from completed remediations
    
    # Get recent tasks
    recent_tasks_result = await db.execute(
        select(RemediationTask)
        .where(RemediationTask.organization_id == str(organization.id))
        .order_by(RemediationTask.requested_at.desc())
        .limit(10)
    )
    recent_tasks = recent_tasks_result.scalars().all()
    
    # Get active workflows
    active_workflows_result = await db.execute(
        select(WorkflowExecution)
        .where(
            and_(
                WorkflowExecution.organization_id == str(organization.id),
                WorkflowExecution.status == "running"
            )
        )
        .order_by(WorkflowExecution.started_at.desc())
        .limit(5)
    )
    active_workflows = active_workflows_result.scalars().all()
    
    return {
        "statistics": {
            "total_tasks": task_stats.total or 0,
            "completed_tasks": task_stats.completed or 0,
            "failed_tasks": task_stats.failed or 0,
            "pending_tasks": task_stats.pending or 0,
            "success_rate": (
                (task_stats.completed or 0) / (task_stats.total or 1) * 100
            ) if task_stats.total else 0,
            "estimated_savings": 12500,  # Mock data
            "auto_remediations": 42  # Mock data
        },
        "recent_tasks": [
            {
                "id": task.id,
                "action_type": task.action_type,
                "resource_type": task.resource_type,
                "status": task.status,
                "requested_at": task.requested_at.isoformat(),
                "dry_run": task.dry_run
            }
            for task in recent_tasks
        ],
        "active_workflows": [
            {
                "id": wf.id,
                "workflow_id": wf.workflow_id,
                "current_step": wf.current_step_id,
                "started_at": wf.started_at.isoformat()
            }
            for wf in active_workflows
        ],
        "last_updated": datetime.utcnow().isoformat()
    }