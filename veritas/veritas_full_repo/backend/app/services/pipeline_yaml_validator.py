
from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.services.meld_pipeline_plugin import validate_license_basename

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

REQUIRED_KEYS = ('name', 'title', 'image', 'modality', 'entrypoint', 'inputs', 'outputs', 'resources')


class PipelineYamlValidator:
    @staticmethod
    def _meld_graph_plugin_checks(parsed: dict[str, Any]) -> list[dict[str, Any]]:
        """When runtime_profile is meld_graph, require plugin.type and plugin.secrets (FreeSurfer + MELD files)."""
        rp = str(parsed.get('runtime_profile', '')).strip().lower()
        plugin = parsed.get('plugin') if isinstance(parsed.get('plugin'), dict) else None
        plugin_type = str(plugin.get('type', '')).strip().lower() if plugin else ''
        if rp != 'meld_graph' and plugin_type != 'meld_graph':
            return []

        if plugin is None or plugin_type != 'meld_graph':
            return [
                {
                    'name': 'meld_plugin_block',
                    'ok': False,
                    'detail': 'runtime_profile is meld_graph: add plugin.type: meld_graph and plugin.secrets',
                }
            ]

        if plugin_type == 'meld_graph' and rp != 'meld_graph':
            return [
                {
                    'name': 'meld_runtime_profile',
                    'ok': False,
                    'detail': 'set runtime_profile: meld_graph to match plugin.type: meld_graph',
                }
            ]

        secrets = plugin.get('secrets') if isinstance(plugin.get('secrets'), dict) else None
        if not secrets:
            return [
                {
                    'name': 'meld_plugin_secrets',
                    'ok': False,
                    'detail': 'plugin.secrets must define freesurfer_license_file and meld_license_file',
                }
            ]

        fs_raw = str(secrets.get('freesurfer_license_file', '')).strip()
        meld_raw = str(secrets.get('meld_license_file', '')).strip()
        fs_ok = validate_license_basename(fs_raw)
        meld_ok = validate_license_basename(meld_raw)
        ok = fs_ok and meld_ok
        detail = 'FreeSurfer + MELD license basenames valid' if ok else 'plugin.secrets: use safe basenames (e.g. license.txt, meld_license.txt)'
        checks = [{'name': 'meld_plugin_secrets', 'ok': ok, 'detail': detail}]

        containers_raw = plugin.get('containers')
        if containers_raw is not None:
            if not isinstance(containers_raw, dict):
                checks.append(
                    {
                        'name': 'meld_containers',
                        'ok': False,
                        'detail': 'plugin.containers must be a mapping with freesurfer and meld image refs',
                    }
                )
            else:
                fs_i = str(containers_raw.get('freesurfer', '') or '').strip()
                meld_i = str(containers_raw.get('meld', '') or '').strip()
                ref_ok = lambda s: bool(re.match(r'^[\w./:-]+$', s))  # noqa: E731
                c_ok = bool(fs_i and meld_i and ref_ok(fs_i) and ref_ok(meld_i))
                checks.append(
                    {
                        'name': 'meld_containers',
                        'ok': c_ok,
                        'detail': 'plugin.containers.freesurfer and .meld set' if c_ok else 'set both container image refs',
                    }
                )

        return checks

    @staticmethod
    def _optional_reports_deliverables_checks(parsed: dict[str, Any]) -> list[dict[str, Any]]:
        """If `reports` is present, it lists user-facing deliverables (PDF/JSON/CSV) sent after the job."""
        if 'reports' not in parsed:
            return []
        reports = parsed.get('reports')
        if not isinstance(reports, list):
            return [
                {
                    'name': 'reports_structure',
                    'ok': False,
                    'detail': 'reports must be a list when present',
                }
            ]
        ok = True
        detail_ok = 'each item has name (user deliverables)'
        for item in reports:
            if not isinstance(item, dict) or not str(item.get('name', '')).strip():
                ok = False
                detail_ok = 'each reports[] entry must be an object with name'
                break
        return [{'name': 'reports_deliverables', 'ok': ok, 'detail': detail_ok}]

    @staticmethod
    def _run_command(command: list[str], timeout: int) -> tuple[bool, str]:
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                check=True,
            )
            detail = (completed.stdout or completed.stderr or 'Image validation succeeded.').strip()
            return True, detail[:500]
        except FileNotFoundError:
            return False, f"Runtime executable not available: {command[0]}"
        except subprocess.TimeoutExpired:
            return False, f"Image validation timed out after {timeout} seconds"
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            return False, detail[:500]

    @staticmethod
    def _docker_validate(image: str, timeout: int) -> tuple[bool, str]:
        if shutil.which('docker') is None:
            return False, 'Docker CLI is not installed on this host.'
        return PipelineYamlValidator._run_command(['docker', 'manifest', 'inspect', image], timeout)

    @staticmethod
    def _apptainer_validate(image: str, timeout: int) -> tuple[bool, str]:
        executable = shutil.which('apptainer') or shutil.which('singularity')
        if executable is None:
            return False, 'Apptainer/Singularity CLI is not installed on this host.'
        return PipelineYamlValidator._run_command([executable, 'inspect', f'docker://{image}'], timeout)

    @staticmethod
    def _normalize_registry_reference(image: str) -> tuple[str, str, str] | None:
        remainder = image
        registry = 'docker.io'
        if '/' not in image:
            remainder = f'library/{image}'
        elif '.' in image.split('/')[0] or ':' in image.split('/')[0]:
            registry, remainder = image.split('/', 1)

        if ':' in remainder:
            repository, tag = remainder.rsplit(':', 1)
        else:
            repository, tag = remainder, 'latest'
        return registry, repository, tag

    @staticmethod
    def _registry_validate(image: str, timeout: int) -> tuple[bool, str]:
        parsed = PipelineYamlValidator._normalize_registry_reference(image)
        if parsed is None:
            return False, 'Unable to parse image reference.'
        registry, repository, tag = parsed

        urls: list[str] = []
        if registry in {'docker.io', 'index.docker.io'}:
            urls.append(f'https://hub.docker.com/v2/repositories/{repository}/tags/{tag}')
        elif registry == 'ghcr.io':
            urls.append(f'https://ghcr.io/v2/{repository}/manifests/{tag}')
        else:
            urls.append(f'https://{registry}/v2/{repository}/manifests/{tag}')

        for url in urls:
            try:
                request = Request(url, headers={'Accept': 'application/vnd.oci.image.manifest.v1+json'})
                with urlopen(request, timeout=timeout) as response:
                    if 200 <= response.status < 300:
                        return True, f'Registry responded with HTTP {response.status}.'
            except HTTPError as exc:
                if exc.code == 401:
                    return False, f'Registry requires authentication for {image}.'
                detail = exc.read().decode('utf-8', errors='ignore')[:300]
                return False, f'Registry returned HTTP {exc.code}. {detail}'.strip()
            except URLError as exc:
                return False, f'Registry lookup failed: {exc.reason}'
            except Exception as exc:  # pragma: no cover - defensive
                return False, f'Registry lookup failed: {exc}'
        return False, 'No registry validation strategy matched this image.'

    @staticmethod
    def _validate_image(image: str) -> tuple[bool, str, str]:
        settings = get_settings()
        mode = settings.image_validation_mode.lower().strip()
        timeout = settings.image_validation_timeout_seconds

        if not image:
            return False, 'skip', 'Container image reference is missing.'
        if mode == 'skip':
            return True, mode, 'Image validation skipped by configuration.'
        if mode == 'docker':
            ok, detail = PipelineYamlValidator._docker_validate(image, timeout)
            return ok, mode, detail
        if mode == 'apptainer':
            ok, detail = PipelineYamlValidator._apptainer_validate(image, timeout)
            return ok, mode, detail
        if mode == 'registry':
            ok, detail = PipelineYamlValidator._registry_validate(image, timeout)
            return ok, mode, detail

        # local/default: prefer the configured runtime, then registry as a fallback
        if settings.runtime_engine == 'apptainer':
            ok, detail = PipelineYamlValidator._apptainer_validate(image, timeout)
            if ok:
                return True, 'apptainer', detail
        else:
            ok, detail = PipelineYamlValidator._docker_validate(image, timeout)
            if ok:
                return True, 'docker', detail
        ok, detail = PipelineYamlValidator._registry_validate(image, timeout)
        return ok, 'registry', detail

    @staticmethod
    def validate(yaml_definition: str) -> dict:
        checks: list[dict[str, Any]] = []
        parsed: dict[str, Any] | None = None
        syntax_ok = False
        detail = 'YAML parser unavailable.' if yaml is None else 'YAML parsed successfully.'
        if yaml is not None:
            try:
                parsed = yaml.safe_load(yaml_definition) or {}
                syntax_ok = isinstance(parsed, dict)
                if not syntax_ok:
                    detail = 'YAML root must be a mapping object.'
            except Exception as exc:
                detail = f'YAML parsing failed: {exc}'
        checks.append({'name': 'yaml_syntax', 'ok': syntax_ok, 'detail': detail})

        if parsed is None:
            parsed = {}

        for key in REQUIRED_KEYS:
            ok = key in parsed and parsed.get(key) not in (None, '', [])
            checks.append({'name': f'required_{key}', 'ok': ok, 'detail': f'{key} present' if ok else f'{key} missing'})

        image = str(parsed.get('image', ''))
        image_ref_ok = bool(re.match(r'^[\w./:-]+$', image))
        checks.append({'name': 'image_reference', 'ok': image_ref_ok, 'detail': image if image_ref_ok else 'Container image reference is missing or invalid'})

        image_validation_mode = get_settings().image_validation_mode
        if image_ref_ok:
            image_ok, image_mode, image_detail = PipelineYamlValidator._validate_image(image)
            checks.append({'name': 'image_accessibility', 'ok': image_ok, 'detail': f'[{image_mode}] {image_detail}'})
        else:
            checks.append({'name': 'image_accessibility', 'ok': False, 'detail': 'Image accessibility skipped because the reference is invalid.'})

        inputs_ok = isinstance(parsed.get('inputs'), list) and len(parsed.get('inputs', [])) > 0
        outputs_ok = isinstance(parsed.get('outputs'), list) and len(parsed.get('outputs', [])) > 0
        checks.append({'name': 'inputs_structure', 'ok': inputs_ok, 'detail': 'inputs list is valid' if inputs_ok else 'inputs must be a non-empty list'})
        checks.append({'name': 'outputs_structure', 'ok': outputs_ok, 'detail': 'outputs list is valid' if outputs_ok else 'outputs must be a non-empty list'})

        resources = parsed.get('resources', {}) if isinstance(parsed.get('resources'), dict) else {}
        cpu_ok = isinstance(resources.get('cpu'), int) and resources.get('cpu', 0) > 0
        checks.append({'name': 'resource_cpu', 'ok': cpu_ok, 'detail': f"cpu={resources.get('cpu')}" if cpu_ok else 'resources.cpu must be a positive integer'})

        checks.extend(PipelineYamlValidator._meld_graph_plugin_checks(parsed))
        checks.extend(PipelineYamlValidator._optional_reports_deliverables_checks(parsed))

        valid = all(item['ok'] for item in checks)
        return {
            'valid': valid,
            'summary': 'Pipeline YAML is valid.' if valid else 'Pipeline YAML needs attention.',
            'checks': checks,
            'normalized': parsed,
            'image_validation_mode': image_validation_mode,
        }
