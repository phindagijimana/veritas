"""MELD YAML plugin parsing and pipeline YAML validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.meld_pipeline_plugin import parse_meld_plugin_config, validate_license_basename
from app.services.pipeline_yaml_validator import PipelineYamlValidator


def _settings_skip_image():
    m = MagicMock()
    m.image_validation_mode = "skip"
    m.image_validation_timeout_seconds = 5
    m.runtime_engine = "docker"
    return m


def test_parse_meld_plugin_defaults_without_plugin_block():
    cfg = parse_meld_plugin_config("name: x\ntitle: t\nimage: img\nmodality: MRI\n")
    assert cfg.freesurfer_license_file == "license.txt"
    assert cfg.meld_license_file == "meld_license.txt"


def test_parse_meld_plugin_full_yaml():
    yml = """
name: meld-graph-fcd
title: M
image: docker.io/phindagijimana321/meld_graph:v2.2.4-nir2
modality: MRI
entrypoint: python x.py
inputs:
  - name: i
    type: BIDS
outputs:
  - name: o
    type: directory
resources:
  cpu: 16
runtime_profile: meld_graph
plugin:
  type: meld_graph
  containers:
    freesurfer: docker.io/freesurfer/fs:7.4.1
    meld: docker.io/phindagijimana321/meld_graph:v2.2.4-nir2
  secrets:
    freesurfer_license_file: license.txt
    meld_license_file: meld_license.txt
  container_env:
    FS_LICENSE: /run/secrets/license.txt
    MELD_LICENSE: /run/secrets/meld_license.txt
"""
    cfg = parse_meld_plugin_config(yml)
    assert cfg.fs_license_container == "/run/secrets/license.txt"
    assert cfg.meld_license_container == "/run/secrets/meld_license.txt"
    assert cfg.freesurfer_image == "docker.io/freesurfer/fs:7.4.1"
    assert cfg.meld_image == "docker.io/phindagijimana321/meld_graph:v2.2.4-nir2"


@patch("app.services.pipeline_yaml_validator.get_settings", return_value=_settings_skip_image())
def test_validate_meld_yaml_plugin_checks(_mock):
    yml = """
name: meld-graph-fcd
title: M
image: docker.io/phindagijimana321/meld_graph:v2.2.4-nir2
modality: MRI
entrypoint: python x.py
inputs:
  - name: i
    type: BIDS
outputs:
  - name: o
    type: directory
resources:
  cpu: 16
runtime_profile: meld_graph
plugin:
  type: meld_graph
  containers:
    freesurfer: docker.io/freesurfer/fs:7.4.1
    meld: docker.io/phindagijimana321/meld_graph:v2.2.4-nir2
  secrets:
    freesurfer_license_file: license.txt
    meld_license_file: meld_license.txt
"""
    out = PipelineYamlValidator.validate(yml)
    assert out["valid"] is True
    names = {c["name"]: c["ok"] for c in out["checks"]}
    assert names.get("meld_plugin_secrets") is True
    assert names.get("meld_containers") is True


@patch("app.services.pipeline_yaml_validator.get_settings", return_value=_settings_skip_image())
def test_validate_rejects_bad_license_basename(_mock):
    yml = """
name: m
title: M
image: docker.io/phindagijimana321/meld_graph:v2.2.4-nir2
modality: MRI
entrypoint: python x.py
inputs:
  - name: i
    type: BIDS
outputs:
  - name: o
    type: directory
resources:
  cpu: 16
runtime_profile: meld_graph
plugin:
  type: meld_graph
  secrets:
    freesurfer_license_file: "../../../etc/passwd"
    meld_license_file: meld_license.txt
"""
    out = PipelineYamlValidator.validate(yml)
    assert out["valid"] is False


def test_validate_license_basename():
    assert validate_license_basename("license.txt") is True
    assert validate_license_basename("../x") is False


@patch("app.services.pipeline_yaml_validator.get_settings", return_value=_settings_skip_image())
def test_validate_optional_reports_deliverables(_mock):
    yml = """
name: custom-pipeline
title: Custom
image: docker.io/phindagijimana321/my-biomarker:v1
modality: MRI
entrypoint: python /app/run.py
inputs:
  - name: i
    type: BIDS
outputs:
  - name: o
    type: directory
resources:
  cpu: 8
reports:
  - name: benchmark_report
    type: pdf
"""
    out = PipelineYamlValidator.validate(yml)
    names = {c["name"]: c for c in out["checks"]}
    assert names["reports_deliverables"]["ok"] is True
    assert out["valid"] is True
