from __future__ import annotations

import json
import shlex

from app.core.config import get_settings
from app.services.meld_pipeline_plugin import MeldPluginConfig, parse_meld_plugin_config


class ContainerRuntimeService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_command(self, image: str, dataset_path: str, output_dir: str) -> str:
        engine = (self.settings.runtime_engine or "docker").lower()
        if engine == "apptainer":
            return (
                f"apptainer run --cleanenv --bind {dataset_path}:/input --bind {output_dir}:/output "
                f"{image} --input /input --output /output"
            )
        return (
            f"docker run --rm -v {dataset_path}:/input -v {output_dir}:/output "
            f"{image} --input /input --output /output"
        )

    def build_meld_graph_runtime_script(
        self,
        *,
        image: str,
        meld_data_dir: str,
        meld_subject_id: str,
        meld_session: str | None,
        staged_dataset_path: str | None,
        default_ideas_staging: str,
        meld_plugin: MeldPluginConfig | None = None,
        pipeline_yaml: str | None = None,
    ) -> str:
        """
        Bash script: prepare BIDS input under meld_data_dir, run MELD new_pt_pipeline (T1, --fastsurfer).

        Staging resolution:
        1) staged_dataset_path from job payload (literal path on compute node)
        2) else VERITAS_STAGED_DATASET_PATH (exported by Atlas → Veritas staging prep)
        3) else default_ideas_staging (e.g. /ood/share/datasets/ideas)

        License files: from `meld_plugin` or parsed from `pipeline_yaml` (`plugin.type: meld_graph`, secrets, container_env).
        """
        plugin = meld_plugin if meld_plugin is not None else parse_meld_plugin_config(pipeline_yaml)
        engine = (self.settings.runtime_engine or "docker").lower()
        exec_image = ((plugin.meld_image or "").strip() or image).strip()
        sub = meld_subject_id.strip()
        if not sub.startswith("sub-"):
            sub = f"sub-{sub}"

        t1_cfg = {"T1": {"session": meld_session, "datatype": "anat", "suffix": "T1w"}}
        bids_json = json.dumps(t1_cfg, indent=2)
        ds_desc = json.dumps({"Name": "IDEAS", "BIDSVersion": "1.0.2"}, indent=2)

        lic_setting = (self.settings.meld_license_host_dir or "").strip()

        if staged_dataset_path and staged_dataset_path.strip():
            staging_line = f"STAGING_ROOT={shlex.quote(staged_dataset_path.strip())}"
        else:
            fallback = shlex.quote(default_ideas_staging)
            staging_line = f'STAGING_ROOT="${{VERITAS_STAGED_DATASET_PATH:-{fallback}}}"'

        meld_q = shlex.quote(meld_data_dir)
        sub_q = shlex.quote(sub)
        img_q = shlex.quote(exec_image)
        fs_b = shlex.quote(plugin.freesurfer_license_file)
        meld_b = shlex.quote(plugin.meld_license_file)
        fs_c = shlex.quote(plugin.fs_license_container)
        meld_c = shlex.quote(plugin.meld_license_container)

        lines: list[str] = [
            "#!/usr/bin/env bash",
            "# Veritas MELD Graph runtime (T1w, Atlas/IDEAS staging; YAML plugin secrets)",
            "set -euo pipefail",
            staging_line,
            f"export MELD_DATA={meld_q}",
            f"SUB={sub_q}",
            f"IMAGE={img_q}",
        ]
        if plugin.freesurfer_image and str(plugin.freesurfer_image).strip():
            lines.append(f'FREESURFER_IMAGE={shlex.quote(str(plugin.freesurfer_image).strip())}')
        lines.extend(
            [
                f"FS_LICENSE_FILE={fs_b}",
                f"MELD_LICENSE_FILE={meld_b}",
                f"FS_LICENSE_CONTAINER={fs_c}",
                f"MELD_LICENSE_CONTAINER={meld_c}",
            ]
        )
        if lic_setting:
            lines.append(f'LICENSE_DIR={shlex.quote(lic_setting)}')
        else:
            lines.append('LICENSE_DIR="${MELD_LICENSE_HOST_DIR:-}"')
        lines.extend(
            [
                'if [[ ! -f "$LICENSE_DIR/$FS_LICENSE_FILE" ]] || [[ ! -f "$LICENSE_DIR/$MELD_LICENSE_FILE" ]]; then',
                '  echo "Missing FreeSurfer or MELD license under $LICENSE_DIR (see pipeline YAML plugin.secrets)." >&2',
                "  exit 1",
                "fi",
                'mkdir -p "$MELD_DATA/input"',
                'if [[ ! -d "$STAGING_ROOT/$SUB" ]]; then',
                '  echo "BIDS subject not found: $STAGING_ROOT/$SUB (Atlas staging / IDEAS path)." >&2',
                "  exit 1",
                "fi",
                'ln -sfn "$STAGING_ROOT/$SUB" "$MELD_DATA/input/$SUB"',
                'cat > "$MELD_DATA/input/meld_bids_config.json" << \'MELD_BIDS_CFG\'',
                bids_json,
                "MELD_BIDS_CFG",
                'cat > "$MELD_DATA/input/dataset_description.json" << \'MELD_DS_DESC\'',
                ds_desc,
                "MELD_DS_DESC",
                'export DOCKER_USER="${DOCKER_USER:-$(id -u):$(id -g)}"',
            ]
        )

        if engine == "apptainer":
            lines.extend(
                [
                    "apptainer run --cleanenv \\",
                    '  --env FS_LICENSE="$FS_LICENSE_CONTAINER" \\',
                    '  --env MELD_LICENSE="$MELD_LICENSE_CONTAINER" \\',
                    '  -B "$MELD_DATA:/data" \\',
                    '  -B "$LICENSE_DIR/$FS_LICENSE_FILE:$FS_LICENSE_CONTAINER:ro" \\',
                    '  -B "$LICENSE_DIR/$MELD_LICENSE_FILE:$MELD_LICENSE_CONTAINER:ro" \\',
                    f'  docker://{exec_image} \\',
                    '  python scripts/new_patient_pipeline/new_pt_pipeline.py -id "$SUB" --fastsurfer',
                ]
            )
        else:
            lines.extend(
                [
                    'docker run --rm --user "$DOCKER_USER" \\',
                    '  -v "$MELD_DATA:/data" \\',
                    '  -v "$LICENSE_DIR/$FS_LICENSE_FILE:$FS_LICENSE_CONTAINER:ro" \\',
                    '  -v "$LICENSE_DIR/$MELD_LICENSE_FILE:$MELD_LICENSE_CONTAINER:ro" \\',
                    '  -e FS_LICENSE="$FS_LICENSE_CONTAINER" \\',
                    '  -e MELD_LICENSE="$MELD_LICENSE_CONTAINER" \\',
                    '  "$IMAGE" \\',
                    '  python scripts/new_patient_pipeline/new_pt_pipeline.py -id "$SUB" --fastsurfer',
                ]
            )

        return "\n".join(lines) + "\n"
