from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


def _extract_download_url(obj: Any) -> str | None:
    if isinstance(obj, str) and obj.startswith("http"):
        return obj
    if isinstance(obj, dict):
        for key in ("downloadUrl", "download_url", "url", "contentUrl", "s3Url", "presignedUrl"):
            val = obj.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val
        for v in obj.values():
            found = _extract_download_url(v)
            if found:
                return found
    if isinstance(obj, list):
        for item in obj:
            found = _extract_download_url(item)
            if found:
                return found
    return None


class PennsieveClient:
    """Optional live Pennsieve calls (Phase 4)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_enabled(self) -> bool:
        return bool(
            self._settings.pennsieve_integration_enabled and self._settings.pennsieve_api_token.strip()
        )

    async def fetch_package_download_url(self, package_id: str) -> str | None:
        if not self.is_enabled():
            return None
        base = self._settings.pennsieve_api_base_url.rstrip("/")
        url = f"{base}/packages/{package_id}"
        headers = {"Authorization": f"Bearer {self._settings.pennsieve_api_token.strip()}"}
        if self._settings.pennsieve_organization_id.strip():
            headers["X-Pennsieve-Organization-Id"] = self._settings.pennsieve_organization_id.strip()

        try:
            async with httpx.AsyncClient(timeout=self._settings.pennsieve_request_timeout_seconds) as client:
                response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("Pennsieve request failed for package %s: %s", package_id, exc)
            return None

        if response.status_code != 200:
            logger.info(
                "Pennsieve package %s returned HTTP %s",
                package_id,
                response.status_code,
            )
            return None

        try:
            data = response.json()
        except ValueError:
            return None

        return _extract_download_url(data)

    def _extract_file_rows(self, obj: Any, depth: int = 0) -> list[dict[str, Any]]:
        """Best-effort file list from Pennsieve package payload (schema varies by API version)."""
        out: list[dict[str, Any]] = []
        if depth > 8:
            return out
        if isinstance(obj, dict):
            files = obj.get("files")
            if isinstance(files, list):
                for f in files:
                    if not isinstance(f, dict):
                        continue
                    path = f.get("path") or f.get("name") or f.get("filename")
                    if not path:
                        continue
                    size = f.get("size") or f.get("sizeInBytes") or 0
                    try:
                        sz = int(size) if size is not None else 0
                    except (TypeError, ValueError):
                        sz = 0
                    out.append({"path": str(path), "size": sz})
            for key in ("children", "content", "items"):
                child = obj.get(key)
                if child is not None:
                    out.extend(self._extract_file_rows(child, depth + 1))
        elif isinstance(obj, list):
            for item in obj:
                out.extend(self._extract_file_rows(item, depth + 1))
        return out

    async def fetch_package_files(self, package_id: str) -> list[dict[str, Any]] | None:
        """Return [{path, size}, ...] when integration is enabled and listing succeeds."""
        if not self.is_enabled():
            return None
        base = self._settings.pennsieve_api_base_url.rstrip("/")
        url = f"{base}/packages/{package_id}"
        headers = {"Authorization": f"Bearer {self._settings.pennsieve_api_token.strip()}"}
        if self._settings.pennsieve_organization_id.strip():
            headers["X-Pennsieve-Organization-Id"] = self._settings.pennsieve_organization_id.strip()

        try:
            async with httpx.AsyncClient(timeout=self._settings.pennsieve_request_timeout_seconds) as client:
                response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("Pennsieve package fetch failed for %s: %s", package_id, exc)
            return None

        if response.status_code != 200:
            return None
        try:
            data = response.json()
        except ValueError:
            return None

        rows = self._extract_file_rows(data)
        return rows if rows else None

    async def fetch_download_manifest(self, package_node_id: str) -> list[dict[str, Any]] | None:
        """
        POST /packages/download-manifest — official manifest with paths and sizes (Pennsieve API).
        Prefer this over GET /packages/{id} heuristics when integration is enabled.
        """
        if not self.is_enabled():
            return None
        base = self._settings.pennsieve_api_base_url.rstrip("/")
        url = f"{base}/packages/download-manifest"
        headers = {
            "Authorization": f"Bearer {self._settings.pennsieve_api_token.strip()}",
            "Content-Type": "application/json",
        }
        if self._settings.pennsieve_organization_id.strip():
            headers["X-Pennsieve-Organization-Id"] = self._settings.pennsieve_organization_id.strip()
        payload = {"nodeIds": [package_node_id]}

        try:
            async with httpx.AsyncClient(timeout=self._settings.pennsieve_request_timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            logger.warning("Pennsieve download-manifest failed for %s: %s", package_node_id, exc)
            return None

        if response.status_code != 200:
            logger.info("download-manifest HTTP %s for %s", response.status_code, package_node_id)
            return None
        try:
            data = response.json()
        except ValueError:
            return None

        rows: list[dict[str, Any]] = []
        entries = data.get("data") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            return None
        for ent in entries:
            if not isinstance(ent, dict):
                continue
            path_parts = ent.get("path")
            if isinstance(path_parts, list):
                path_str = "/".join(str(p) for p in path_parts)
            else:
                path_str = str(ent.get("fileName") or ent.get("path") or "")
            if not path_str:
                continue
            size = ent.get("size") or 0
            try:
                sz = int(size) if size is not None else 0
            except (TypeError, ValueError):
                sz = 0
            rows.append({"path": path_str, "size": sz})
        return rows if rows else None

    async def export_package_job(self, package_id: str) -> str | None:
        """
        PUT /packages/{id}/export — may return async export job metadata (API-specific).
        Returns a job or export reference string when the response includes one.
        """
        if not self.is_enabled():
            return None
        base = self._settings.pennsieve_api_base_url.rstrip("/")
        url = f"{base}/packages/{package_id}/export"
        headers = {"Authorization": f"Bearer {self._settings.pennsieve_api_token.strip()}"}
        if self._settings.pennsieve_organization_id.strip():
            headers["X-Pennsieve-Organization-Id"] = self._settings.pennsieve_organization_id.strip()

        try:
            async with httpx.AsyncClient(timeout=self._settings.pennsieve_request_timeout_seconds) as client:
                response = await client.put(url, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("Pennsieve export failed for %s: %s", package_id, exc)
            return None

        if response.status_code not in (200, 202):
            return None
        try:
            data = response.json()
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        for key in ("id", "jobId", "exportId", "taskId"):
            val = data.get(key)
            if isinstance(val, str) and val:
                return val
        return None
