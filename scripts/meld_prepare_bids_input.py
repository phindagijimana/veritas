#!/usr/bin/env python3
"""
Link BIDS data into meld_docker_data/input for MELD Graph (Docker volume /data).

Per https://meld-graph.readthedocs.io/en/latest/prepare_data.html — writes
meld_bids_config.json (T1-only by default) and dataset_description.json under input/.

Usage:
  export VALIDATOR_ROOT=/path/to/validator
  python3 scripts/meld_prepare_bids_input.py --bids-root /ood/share/datasets/ideas
  python3 scripts/meld_prepare_bids_input.py --bids-root /path/to/bids --subject sub-01
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _find_t1_layout(bids_root: Path) -> list[tuple[str, str | None, Path]]:
    """Return (subject_id, session_name_without_ses_prefix_or_None, t1_nifti_path)."""
    seen: set[tuple[str, str | None, str]] = set()
    out: list[tuple[str, str | None, Path]] = []
    for f in sorted(bids_root.glob("sub-*/anat/*T1w*.nii*")):
        if not f.is_file():
            continue
        sub = f.parent.parent.name
        key = (sub, None, str(f.resolve()))
        if key not in seen:
            seen.add(key)
            out.append((sub, None, f))
    for f in sorted(bids_root.glob("sub-*/ses-*/anat/*T1w*.nii*")):
        if not f.is_file():
            continue
        ses_dir = f.parent.parent
        sub_dir = ses_dir.parent
        sub = sub_dir.name
        ses = ses_dir.name
        session = ses[4:] if ses.startswith("ses-") else ses
        key = (sub, session, str(f.resolve()))
        if key not in seen:
            seen.add(key)
            out.append((sub, session, f))
    return out


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    default_meld = root / "meld_docker_data"
    ap = argparse.ArgumentParser(description="Prepare MELD input/ from a BIDS dataset (T1-only).")
    ap.add_argument(
        "--bids-root",
        required=True,
        type=Path,
        help="BIDS dataset root (e.g. IDEAS copy or Atlas secondary path)",
    )
    ap.add_argument(
        "--meld-data",
        type=Path,
        default=Path(os.environ.get("VALIDATOR_ROOT", str(root))) / "meld_docker_data",
        help="Directory mounted as /data in the MELD container",
    )
    ap.add_argument("--subject", help="BIDS subject id (e.g. sub-01). Default: first subject with T1w.")
    ap.add_argument(
        "--reset-input",
        action="store_true",
        help="Remove existing input/ before linking (recommended when switching subjects).",
    )
    args = ap.parse_args()

    bids_root = args.bids_root.resolve()
    if not bids_root.is_dir():
        print(f"ERROR: BIDS root not found: {bids_root}", file=sys.stderr)
        sys.exit(1)

    found = _find_t1_layout(bids_root)
    if not found:
        print(f"ERROR: No T1w NIfTI under {bids_root} (expected sub-*/anat/ or sub-*/ses-*/anat/).", file=sys.stderr)
        sys.exit(1)

    chosen: tuple[str, str | None, Path] | None = None
    if args.subject:
        sid = args.subject if args.subject.startswith("sub-") else f"sub-{args.subject}"
        for sub, ses, p in found:
            if sub == sid:
                chosen = (sub, ses, p)
                break
        if chosen is None:
            print(f"ERROR: No T1w for {sid} under {bids_root}", file=sys.stderr)
            sys.exit(1)
    else:
        chosen = found[0]

    sub_id, session, t1_path = chosen
    meld_data = args.meld_data.resolve()
    input_dir = meld_data / "input"

    if args.reset_input and input_dir.exists():
        import shutil

        shutil.rmtree(input_dir)

    input_dir.mkdir(parents=True, exist_ok=True)

    # Symlink only this subject tree into input/ (keeps meld_data small).
    src_sub_dir = bids_root / sub_id
    if not src_sub_dir.is_dir():
        print(f"ERROR: {src_sub_dir}", file=sys.stderr)
        sys.exit(1)
    dst_sub = input_dir / sub_id
    if dst_sub.exists() or dst_sub.is_symlink():
        dst_sub.unlink()
    dst_sub.symlink_to(src_sub_dir, target_is_directory=True)

    bids_cfg: dict = {
        "T1": {
            "session": session,
            "datatype": "anat",
            "suffix": "T1w",
        }
    }
    (input_dir / "meld_bids_config.json").write_text(json.dumps(bids_cfg, indent=2), encoding="utf-8")

    ds_desc = {
        "Name": "IDEAS (or linked BIDS) — T1w for MELD",
        "BIDSVersion": "1.0.2",
    }
    if (bids_root / "dataset_description.json").is_file():
        try:
            ds_desc = json.loads((bids_root / "dataset_description.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    (input_dir / "dataset_description.json").write_text(json.dumps(ds_desc, indent=2), encoding="utf-8")

    print("Prepared MELD input:")
    print(f"  meld_data:  {meld_data}")
    print(f"  input:      {input_dir}")
    print(f"  subject:    {sub_id}")
    print(f"  session:    {session!r}")
    print(f"  T1w file:   {t1_path}")
    print()
    print("Run prediction (T1-only; --fastsurfer recommended):")
    print(
        f'  cd "{root}" && export VALIDATOR_ROOT="{root}" DOCKER_USER="$(id -u):$(id -g)" && '
        f'docker compose -f scripts/meld-compose.validator.yml run --rm meld_graph '
        f'python scripts/new_patient_pipeline/new_pt_pipeline.py -id {sub_id} --fastsurfer'
    )


if __name__ == "__main__":
    main()
