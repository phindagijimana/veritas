"""Generate a syntactically valid 1×1×1 NIfTI-1 placeholder for the
synthetic BIDS fixture under tests/fixtures/bids/. See the fixture's
README for context. The output is ~200 bytes, contains exactly one voxel
of zero, and exists solely to satisfy structural BIDS validators."""
from __future__ import annotations

import argparse
import gzip
import struct
from pathlib import Path


def write_minimal_nifti(target: Path) -> int:
    hdr = bytearray(352)
    struct.pack_into("<i", hdr, 0, 348)  # sizeof_hdr
    struct.pack_into("<8h", hdr, 40, 3, 1, 1, 1, 1, 1, 1, 1)  # dim
    struct.pack_into("<h", hdr, 70, 2)  # datatype = uint8
    struct.pack_into("<h", hdr, 72, 8)  # bitpix
    struct.pack_into("<8f", hdr, 76, 1.0, 1.0, 1.0, 1.0, 0, 0, 0, 0)  # pixdim
    struct.pack_into("<f", hdr, 108, 352.0)  # vox_offset
    hdr[344:348] = b"n+1\0"  # NIfTI-1 magic, single-file form
    img = b"\x00"  # one voxel of zero
    target.parent.mkdir(parents=True, exist_ok=True)
    blob = gzip.compress(bytes(hdr) + img)
    target.write_bytes(blob)
    return len(blob)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("tests/fixtures/bids/sub-001/anat/sub-001_T1w.nii.gz"),
    )
    args = ap.parse_args()
    n = write_minimal_nifti(args.output)
    print(f"wrote {args.output} ({n} bytes)")


if __name__ == "__main__":
    main()
