from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
import json

class WorkflowStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

class WorkflowStepType(Enum):
    APPROVAL = "approval"
    ACTION = "action"
    NOTIFICATION = "notification"
    CONDITION = "condition"

class WorkflowTriggerType(Enum):
    SECURITY_FINDING = "security_finding"
    COST_ANOMALY = "cost_anomaly"
    COMPLIANCE_VIOLATION = "compliance_violation"
    MANUAL = "manual"
    SCHEDULED = "scheduled"

@dataclass
class WorkflowStep:
    id: str
    step_type: WorkflowStepType
    title: str
    description: str
    config: Dict[str, Any]
    next_steps: List[str]  # IDs of next steps
    timeout_minutes: int = 60
    required: bool = True

@dataclass
class Workflow:
    id: str
    name: str
    description: str
    organization_id: str
    trigger_type: WorkflowTriggerType
    trigger_conditions: Dict[str, Any]
    steps: List[WorkflowStep]
    status: WorkflowStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    version: int = 1

class WorkflowManager:
    """Manage remediation workflows and automation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_workflow(
        self,
        organization_id: str,
        name: str,
        description: str,
        trigger_type: str,
        trigger_conditions: Dict[str, Any],
        steps: List[Dict[str, Any]],
        created_by: str
    ) -> Workflow:
        """Create a new remediation workflow."""
        from app.models.remediation import RemediationWorkflow
        
        workflow_id = f"wf_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Create workflow steps
        workflow_steps = []
        for step_data in steps:
            step = WorkflowStep(
                id=f"step_{len(workflow_steps)}",
                step_type=WorkflowStepType(step_data['step_type']),
                title=step_data['title'],
                description=step_data.get('description', ''),
                config=step_data.get('config', {}),
                next_steps=step_data.get('next_steps', []),
                timeout_minutes=step_data.get('timeout_minutes', 60),
                required=step_data.get('required', True)
            )
            workflow_steps.append(step)
        
        workflow = RemediationWorkflow(
            id=workflow_id,
            organization_id=organization_id,
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_conditions=trigger_conditions,
            steps=json.dumps([step.__dict__ for step in workflow_steps]),
            status=WorkflowStatus.DRAFT.value,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            version=1
        )
        
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        
        return self._model_to_workflow(workflow)
    
    async def trigger_workflow(
        self,
        trigger_type: str,
        trigger_data: Dict[str, Any],
        organization_id: str
    ) -> List[Workflow]:
        """Find and trigger matching workflows."""
        from app.models.remediation import RemediationWorkflow
        
        result = await self.db.execute(
            select(RemediationWorkflow).where(
                and_(
                    RemediationWorkflow.organization_id == organization_id,
                    RemediationWorkflow.status == WorkflowStatus.ACTIVE.value,
                    RemediationWorkflow.trigger_type == trigger_type
                )
            )
        )
        workflows = result.scalars().all()
        
        triggered_workflows = []
        
        for workflow_model in workflows:
            workflow = self._model_to_workflow(workflow_model)
            
            # Check if workflow conditions match
            if await self._check_conditions(workflow.trigger_conditions, trigger_data):
                triggered_workflows.append(workflow)
                
                # Start workflow execution
                await self._start_workflow_execution(workflow, trigger_data)
        
        return triggered_workflows
    
    async def _check_conditions(
        self,
        conditions: Dict[str, Any],
        data: Dict[str, Any]
    ) -> bool:
        """Check if workflow conditions are met."""
        if not conditions:
            return True
        
        # Check severity condition
        if 'severity' in conditions:
            if data.get('severity') not in conditions['severity']:
                return False
        
        # Check resource type condition
        if 'resource_types' in conditions:
            if data.get('resource_type') not in conditions['resource_types']:
                return False
        
        # Check cost threshold condition
        if 'cost_threshold' in conditions:
            cost = data.get('cost', 0)
            threshold = conditions['cost_threshold']
            if cost < threshold:
                return False
        
        # Check custom conditions
        if 'custom' in conditions:
            # Evaluate custom condition logic
            # This could be a simple expression evaluator
            pass
        
        return True
    
    async def _start_workflow_execution(
        self,
        workflow: Workflow,
        trigger_data: Dict[str, Any]
    ):
        """Start executing a workflow."""
        from app.models.remediation import WorkflowExecution
        
        execution_id = f"exec_{workflow.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow.id,
            organization_id=workflow.organization_id,
            status="running",
            trigger_data=json.dumps(trigger_data),
            current_step_id=workflow.steps[0].id if workflow.steps else None,
            execution_log=json.dumps([]),
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(execution)
        await self.db.commit()
        
        # Process first step
        await self._process_workflow_step(execution_id, workflow.steps[0])
    
    async def _process_workflow_step(
        self,
        execution_id: str,
        step: WorkflowStep
    ):
        """Process a workflow step."""
        from app.models.remediation import WorkflowExecution
        
        # Get execution
        result = await self.db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id
            )
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            return
        
        # Update execution log
        log = json.loads(execution.execution_log or '[]')
        log.append({
            "step_id": step.id,
            "step_type": step.step_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "action": "started"
        })
        
        execution.execution_log = json.dumps(log)
        execution.current_step_id = step.id
        await self.db.commit()
        
        # Process based on step type
        if step.step_type == WorkflowStepType.APPROVAL:
            await self._process_approval_step(execution, step)
        
        elif step.step_type == WorkflowStepType.ACTION:
            await self._process_action_step(execution, step)
        
        elif step.step_type == WorkflowStepType.NOTIFICATION:
            await self._process_notification_step(execution, step)
    
    async def _process_approval_step(
        self,
        execution,
        step: WorkflowStep
    ):
        """Process an approval step."""
        from app.models.remediation import WorkflowApproval
        
        # Create approval request
        approval = WorkflowApproval(
            workflow_execution_id=execution.id,
            step_id=step.id,
            approvers=json.dumps(step.config.get('approvers', [])),
            status="pending",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=step.timeout_minutes)
        )
        
        self.db.add(approval)
        await self.db.commit()
        
        # Send notifications to approvers
        await self._send_approval_notifications(approval, step)
    
    async def _process_action_step(
        self,
        execution,
        step: WorkflowStep
    ):
        """Process an action step."""
        # Execute the action using RemediationEngine
        from app.services.remediation.engine import RemediationEngine
        
        engine = RemediationEngine(self.db)
        trigger_data = json.loads(execution.trigger_data)
        
        # Create remediation action from step config
        action_config = step.config.get('action', {})
        
        # Execute action
        result = await engine.execute_remediation(
            action=...,
            executed_by="workflow_system",
            dry_run=False
        )
        
        # Update execution log
        log = json.loads(execution.execution_log or '[]')
        log.append({
            "step_id": step.id,
            "timestamp": datetime.utcnow().isoformat(),
            "action": "executed",
            "result": result
        })
        
        execution.execution_log = json.dumps(log)
        await self.db.commit()
        
        # Move to next step
        if step.next_steps:
            next_step_id = step.next_steps[0]  # Simple linear flow
            # Find and process next step
            pass
    
    async def _process_notification_step(
        self,
        execution,
        step: WorkflowStep
    ):
        """Process a notification step."""
        # Send notifications based on step config
        notification_config = step.config
        
        # This would integrate with email/Slack/etc.
        # For now, just log
        log = json.loads(execution.execution_log or '[]')
        log.append({
            "step_id": step.id,
            "timestamp": datetime.utcnow().isoformat(),
            "action": "notification_sent",
            "config": notification_config
        })
        
        execution.execution_log = json.dumps(log)
        await self.db.commit()
    
    async def _send_approval_notifications(self, approval, step: WorkflowStep):
        """Send approval request notifications."""
        # This would send email/Slack notifications to approvers
        # For now, just log
        print(f"Approval requested for workflow step {step.id}")
    
    async def approve_workflow_step(
        self,
        execution_id: str,
        step_id: str,
        approver: str,
        comment: str = ""
    ) -> bool:
        """Approve a workflow step."""
        from app.models.remediation import WorkflowApproval
        
        result = await self.db.execute(
            select(WorkflowApproval).where(
                and_(
                    WorkflowApproval.workflow_execution_id == execution_id,
                    WorkflowApproval.step_id == step_id,
                    WorkflowApproval.status == "pending"
                )
            )
        )
        approval = result.scalar_one_or_none()
        
        if not approval:
            return False
        
        approval.status = "approved"
        approval.approved_by = approver
        approval.approved_at = datetime.utcnow()
        approval.comment = comment
        
        await self.db.commit()
        
        # Continue workflow execution
        await self._continue_workflow_after_approval(execution_id, step_id)
        
        return True
    
    async def _continue_workflow_after_approval(
        self,
        execution_id: str,
        step_id: str
    ):
        """Continue workflow execution after approval."""
        from app.models.remediation import WorkflowExecution
        
        result = await self.db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id
            )
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            return
        
        # Get workflow and find next step
        workflow_result = await self.db.execute(
            select(Workflow).where(
                Workflow.id == execution.workflow_id
            )
        )
        workflow_model = workflow_result.scalar_one_or_none()
        
        if not workflow_model:
            return
        
        workflow = self._model_to_workflow(workflow_model)
        
        # Find current step and next step
        current_step = next((s for s in workflow.steps if s.id == step_id), None)
        if current_step and current_step.next_steps:
            next_step_id = current_step.next_steps[0]
            next_step = next((s for s in workflow.steps if s.id == next_step_id), None)
            
            if next_step:
                await self._process_workflow_step(execution_id, next_step)
    
    def _model_to_workflow(self, model) -> Workflow:
        """Convert SQLAlchemy model to Workflow dataclass."""
        steps_data = json.loads(model.steps or '[]')
        steps = [
            WorkflowStep(
                id=step['id'],
                step_type=WorkflowStepType(step['step_type']),
                title=step['title'],
                description=step['description'],
                config=step['config'],
                next_steps=step['next_steps'],
                timeout_minutes=step.get('timeout_minutes', 60),
                required=step.get('required', True)
            )
            for step in steps_data
        ]
        
        return Workflow(
            id=model.id,
            name=model.name,
            description=model.description,
            organization_id=model.organization_id,
            trigger_type=WorkflowTriggerType(model.trigger_type),
            trigger_conditions=json.loads(model.trigger_conditions or '{}'),
            steps=steps,
            status=WorkflowStatus(model.status),
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version
        )