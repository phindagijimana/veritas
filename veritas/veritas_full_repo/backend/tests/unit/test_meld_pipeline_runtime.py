"""Unit tests for MELD Graph runtime planning (no database)."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

from app.schemas.hpc import SlurmJobSubmitRequest, SlurmResourcesPayload
from app.services.container_runtime import ContainerRuntimeService
from app.services.pipeline_runner import PipelineRunnerService
from app.services.slurm_service import SlurmResourcesConfig, SlurmService


def _mock_settings(**kwargs):
    m = MagicMock()
    m.meld_license_host_dir = kwargs.get("meld_license_host_dir", "/lic")
    m.meld_ideas_default_staging_path = kwargs.get("meld_ideas_default_staging_path", "/ood/share/datasets/ideas")
    m.runtime_engine = kwargs.get("runtime_engine", "docker")
    return m


def test_meld_runtime_script_contains_staging_and_subject():
    with patch("app.services.container_runtime.get_settings", return_value=_mock_settings()):
        rt = ContainerRuntimeService()
        script = rt.build_meld_graph_runtime_script(
            image="meldproject/meld_graph:latest",
            meld_data_dir="/tmp/job/meld_docker_data",
            meld_subject_id="sub-01",
            meld_session=None,
            staged_dataset_path="/data/staging/ideas",
            default_ideas_staging="/ood/share/datasets/ideas",
        )
    assert "STAGING_ROOT=" in script
    assert "sub-01" in script
    assert "new_pt_pipeline.py" in script
    assert "meld_bids_config.json" in script
    assert "FS_LICENSE_CONTAINER=" in script
    assert "MELD_LICENSE_CONTAINER=" in script
    assert "meldproject/meld_graph:latest" in script


def test_meld_runtime_script_uses_yaml_plugin_mounts():
    yml = """
runtime_profile: meld_graph
image: docker.io/meldproject/meld_graph:latest
plugin:
  type: meld_graph
  containers:
    freesurfer: docker.io/freesurfer/fs:7.4.1
    meld: docker.io/meldproject/meld_graph:latest
  secrets:
    freesurfer_license_file: license.txt
    meld_license_file: meld_license.txt
  container_env:
    FS_LICENSE: /run/secrets/license.txt
    MELD_LICENSE: /run/secrets/meld_license.txt
"""
    with patch("app.services.container_runtime.get_settings", return_value=_mock_settings()):
        rt = ContainerRuntimeService()
        script = rt.build_meld_graph_runtime_script(
            image="meldproject/meld_graph:latest",
            meld_data_dir="/tmp/m",
            meld_subject_id="01",
            meld_session=None,
            staged_dataset_path="/data/s",
            default_ideas_staging="/ood/share/datasets/ideas",
            pipeline_yaml=yml,
        )
    assert "$LICENSE_DIR/$FS_LICENSE_FILE:$FS_LICENSE_CONTAINER" in script
    assert '-e FS_LICENSE="$FS_LICENSE_CONTAINER"' in script
    assert "FREESURFER_IMAGE=" in script
    assert "docker.io/freesurfer/fs:7.4.1" in script


def test_slurm_script_embeds_multiline_runtime_via_base64():
    cfg = SlurmResourcesConfig(job_name="j", partition="p", cpus=1, memory_gb=8, wall_time="01:00:00")
    multiline = "#!/bin/bash\necho hello\necho world\n"
    script = SlurmService.build_execution_script(
        config=cfg,
        runtime_command=multiline,
        runtime_manifest_path="/tmp/m.json",
        remote_workdir="/tmp/w",
        stdout_path="/tmp/o",
        stderr_path="/tmp/e",
    )
    assert "base64" in script
    assert base64.b64encode(multiline.encode()).decode() in script


@patch("app.services.pipeline_runner.ArtifactStorageService")
def test_pipeline_runner_meld_manifest(mock_storage_cls, tmp_path):
    root = tmp_path / "artifacts"
    root.mkdir()
    manifest_path = root / "run_manifest.json"
    mock_storage = MagicMock()
    mock_storage.job_layout.return_value = {
        "local_run_dir": str(root / "run"),
        "runtime_manifest_path": str(manifest_path),
        "metrics_path": str(root / "m.json"),
        "results_csv_path": str(root / "r.csv"),
        "report_path": str(root / "r.pdf"),
        "report_json_path": str(root / "rj.json"),
        "report_html_path": str(root / "rh.html"),
    }
    mock_storage_cls.return_value = mock_storage

    with patch("app.services.container_runtime.get_settings", return_value=_mock_settings()):
        with patch("app.services.pipeline_runner.get_settings", return_value=_mock_settings()):
            runner = PipelineRunnerService()
            payload = SlurmJobSubmitRequest(
                job_name="meld",
                pipeline="meldproject/meld_graph:latest",
                dataset="ideas",
                runtime_profile="meld_graph",
                meld_subject_id="sub-01",
                resources=SlurmResourcesPayload(),
            )
            plan = runner.build_plan("REQ-1", "meld", "meldproject/meld_graph:latest", "ideas", job_payload=payload)
    assert "meld_docker_data" in plan.runtime_command
    assert "sub-01" in plan.runtime_command
    assert plan.manifest.get("runtime_profile") == "meld_graph"
