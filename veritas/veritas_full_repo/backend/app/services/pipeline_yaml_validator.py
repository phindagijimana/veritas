
from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

REQUIRED_KEYS = ('name', 'title', 'image', 'modality', 'entrypoint', 'inputs', 'outputs', 'resources')


class PipelineYamlValidator:
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

        valid = all(item['ok'] for item in checks)
        return {
            'valid': valid,
            'summary': 'Pipeline YAML is valid.' if valid else 'Pipeline YAML needs attention.',
            'checks': checks,
            'normalized': parsed,
            'image_validation_mode': image_validation_mode,
        }
