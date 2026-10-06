from pathlib import Path

import pytest

from src.company.deployment import DeploymentConfig, DeploymentService


@pytest.mark.asyncio
async def test_deployment_service_runs_command(tmp_path: Path):
    service = DeploymentService()
    config = DeploymentConfig(
        command=("python", "-c", "print('deployed')"),
        rollback_command=("python", "-c", "print('rolled back')"),
    )

    result = await service.deploy(config, tmp_path)

    assert result.success
    assert result.status == "deployed"
    assert result.rollback_available


@pytest.mark.asyncio
async def test_deployment_service_rolls_back(tmp_path: Path):
    service = DeploymentService()
    config = DeploymentConfig(
        command=("python", "-c", "raise SystemExit(1)"),
        rollback_command=("python", "-c", "print('rollback')"),
    )

    result = await service.rollback(config, tmp_path)

    assert result.success
    assert result.status == "rolled_back"
