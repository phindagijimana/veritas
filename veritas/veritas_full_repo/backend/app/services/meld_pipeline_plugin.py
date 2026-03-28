"""Parse MELD Graph pipeline YAML `plugin` block (FreeSurfer + MELD licenses, container paths)."""

from __future__ import annotations

import re
from dataclasses import dataclass

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


_SAFE_BASENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")


def validate_license_basename(raw: str) -> bool:
    s = (raw or "").strip()
    if s in {".", ".."}:
        return False
    return bool(_SAFE_BASENAME.match(s))


@dataclass(frozen=True)
class MeldPluginConfig:
    """Host files live under LICENSE_DIR / MELD_LICENSE_HOST_DIR; container paths match MELD/FreeSurfer env."""

    freesurfer_license_file: str = "license.txt"
    meld_license_file: str = "meld_license.txt"
    fs_license_container: str = "/run/secrets/license.txt"
    meld_license_container: str = "/run/secrets/meld_license.txt"
    # Optional: separate images declared in YAML under plugin.containers.{freesurfer,meld}
    freesurfer_image: str | None = None
    meld_image: str | None = None


def _safe_license_basename(raw: str, default: str) -> str:
    s = (raw or "").strip()
    if not s:
        return default
    if not _SAFE_BASENAME.match(s) or "/" in s or s in {".", ".."}:
        raise ValueError(f"Invalid license file basename: {raw!r}")
    return s


def parse_meld_plugin_config(yaml_definition: str | None) -> MeldPluginConfig:
    """
    Read `plugin.type: meld_graph` and nested `secrets` / `container_env` from pipeline YAML.
    If YAML is missing or has no meld plugin block, return defaults (official MELD image layout).
    """
    if not yaml_definition or yaml is None:
        return MeldPluginConfig()

    try:
        parsed = yaml.safe_load(yaml_definition) or {}
    except Exception:
        return MeldPluginConfig()

    if not isinstance(parsed, dict):
        return MeldPluginConfig()

    plugin = parsed.get("plugin")
    if not isinstance(plugin, dict):
        return MeldPluginConfig()

    if str(plugin.get("type", "")).strip().lower() != "meld_graph":
        return MeldPluginConfig()

    secrets = plugin.get("secrets")
    if not isinstance(secrets, dict):
        secrets = {}

    fs_file = _safe_license_basename(str(secrets.get("freesurfer_license_file", "") or ""), "license.txt")
    meld_file = _safe_license_basename(str(secrets.get("meld_license_file", "") or ""), "meld_license.txt")

    env = plugin.get("container_env")
    if not isinstance(env, dict):
        env = {}

    fs_container = (env.get("FS_LICENSE") or "").strip()
    meld_container = (env.get("MELD_LICENSE") or "").strip()

    if not fs_container:
        fs_container = f"/run/secrets/{fs_file}"
    if not meld_container:
        meld_container = f"/run/secrets/{meld_file}"

    containers = plugin.get("containers")
    fs_img: str | None = None
    meld_img: str | None = None
    if isinstance(containers, dict):
        fs_img = str(containers.get("freesurfer", "") or "").strip() or None
        meld_img = str(containers.get("meld", "") or "").strip() or None

    top_image = str(parsed.get("image", "") or "").strip()
    if not meld_img and top_image:
        meld_img = top_image

    return MeldPluginConfig(
        freesurfer_license_file=fs_file,
        meld_license_file=meld_file,
        fs_license_container=fs_container,
        meld_license_container=meld_container,
        freesurfer_image=fs_img,
        meld_image=meld_img,
    )
