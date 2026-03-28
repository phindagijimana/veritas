from __future__ import annotations

from app.core.config import get_settings


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
