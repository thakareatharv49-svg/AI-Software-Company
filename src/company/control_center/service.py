from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from threading import Lock

from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from src.agents.execution.executor import AgentExecutor
from src.agents.models.contracts import AgentResult
from src.agents.registry.registry import AgentRegistry
from src.company.audit import MissionAuditEntry
from src.company.autonomous_factory_runner import FactoryAutonomousRunner
from src.company.autonomous_project import AutonomousProjectRequest, AutonomousProjectRunner
from src.company.ceo.models import Mission as CEOMission
from src.company.execution.pipeline import CompanyExecutionPipeline
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.models import MissionPlan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission, CompanyState
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory
from src.company.project_generator import OllamaProjectGenerator
from src.company.project_outputs import ProjectOutputManifest
from src.company.research.engine import StaticResearchProvider
from src.manager.models.contracts import Mission as ManagerMission, TaskPlanItem
from src.projects.models.contracts import ProjectCreateRequest
from src.qa.models.contracts import QATestRequest
from src.runtime.providers.ollama import OllamaProvider
from src.runtime.service import AIRuntime
