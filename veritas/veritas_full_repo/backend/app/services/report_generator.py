from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.job import Job
from app.models.request import EvaluationRequest
from app.services.artifact_storage import ArtifactStorageService
from app.services.metrics_parser import MetricsParserService


class ReportGeneratorService:
    """Builds the researcher-facing benchmark report bundle.

    The implementation stays dependency-light so the scaffold can run in minimal
    environments. It generates:
    - PDF summary report (minimal valid PDF)
    - JSON report payload
    - CSV metrics table
    - HTML summary for easy preview/debugging
    """

    @staticmethod
    def _context(request: EvaluationRequest, job: Job | None, metrics: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "generated_at": now,
            "request_id": request.request_code,
            "pipeline": getattr(job, "pipeline_ref", None) or "unknown-pipeline",
            "dataset": getattr(job, "dataset_name", None) or "unknown-dataset",
            "runtime_engine": getattr(job, "runtime_engine", None) or "unknown-runtime",
            "partition": getattr(job, "partition", None) or "unknown-partition",
            "resources": getattr(job, "resources", None) or "unknown-resources",
            "status": request.status,
            "report_status": request.report_status,
            "admin_note": request.admin_note,
            "metrics": metrics,
            "artifacts": {
                "runtime_manifest_path": getattr(job, "runtime_manifest_path", None),
                "metrics_path": getattr(job, "metrics_path", None),
                "results_csv_path": getattr(job, "results_csv_path", None),
                "stdout_path": getattr(job, "stdout_path", None),
                "stderr_path": getattr(job, "stderr_path", None),
            },
        }

    @staticmethod
    def _html_report(context: dict[str, Any]) -> str:
        rows = "".join(
            f"<tr><td>{key}</td><td>{value}</td></tr>" for key, value in context["metrics"].items()
        )
        return f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <title>Veritas Report {context['request_id']}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 32px; color: #16325c; }}
      h1 {{ color: #0f2f6b; }}
      .meta {{ margin-bottom: 24px; }}
      .meta p {{ margin: 4px 0; }}
      table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
      th, td {{ border: 1px solid #d7e2f2; padding: 8px; text-align: left; }}
      th {{ background: #eaf1fb; }}
    </style>
  </head>
  <body>
    <h1>Veritas Benchmark Report</h1>
    <div class=\"meta\">
      <p><strong>Request:</strong> {context['request_id']}</p>
      <p><strong>Dataset:</strong> {context['dataset']}</p>
      <p><strong>Pipeline:</strong> {context['pipeline']}</p>
      <p><strong>Runtime:</strong> {context['runtime_engine']}</p>
      <p><strong>Partition:</strong> {context['partition']}</p>
      <p><strong>Resources:</strong> {context['resources']}</p>
      <p><strong>Generated:</strong> {context['generated_at']}</p>
    </div>
    <h2>Metrics Summary</h2>
    <table>
      <thead><tr><th>Metric</th><th>Value</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </body>
</html>
"""

    @staticmethod
    def _pdf_bytes(text: str) -> bytes:
        # Minimal valid single-page PDF. Escapes are intentionally simple because
        # the generated text is short and ASCII-friendly.
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 50 760 Td ({safe}) Tj ET"
        objects = [
            "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
            "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
            "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
            "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
            f"5 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj\n",
        ]
        pdf = b"%PDF-1.4\n"
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf))
            pdf += obj.encode("utf-8")
        xref_start = len(pdf)
        xref = f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
        xref += "".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
        trailer = f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
        pdf += xref.encode("utf-8") + trailer.encode("utf-8")
        return pdf

    @classmethod
    def generate_bundle(
        cls,
        request: EvaluationRequest,
        job: Job | None,
        storage: ArtifactStorageService,
    ) -> dict[str, str]:
        request_code = request.request_code
        layout = storage.job_layout(request_code, getattr(job, "job_name", request_code))
        metrics_path = getattr(job, "metrics_path", None) or layout["metrics_path"]
        report_path = getattr(job, "report_path", None) or layout["report_path"]
        csv_path = getattr(job, "results_csv_path", None) or layout["results_csv_path"]
        report_json_path = layout["report_json_path"]
        report_html_path = layout["report_html_path"]

        metrics = MetricsParserService.parse_metrics_file(metrics_path)
        context = cls._context(request, job, metrics)

        storage.write_json(report_json_path, context)
        storage.write_csv(csv_path, ["metric", "value"], MetricsParserService.tabular_rows(metrics))
        storage.write_text(report_html_path, cls._html_report(context))

        pdf_text = (
            f"Veritas Benchmark Report | Request {context['request_id']} | Dataset {context['dataset']} | "
            f"Pipeline {context['pipeline']} | Dice {metrics.get('dice')} | Sensitivity {metrics.get('sensitivity')} | "
            f"Specificity {metrics.get('specificity')} | AUC {metrics.get('auc')}"
        )
        storage.write_bytes(report_path, cls._pdf_bytes(pdf_text))

        # Ensure metrics.json exists even when the pipeline has not produced it yet.
        if not Path(metrics_path).exists():
            storage.write_json(metrics_path, metrics)

        return {
            "pdf_path": report_path,
            "json_path": report_json_path,
            "csv_path": csv_path,
            "html_path": report_html_path,
            "metrics_path": metrics_path,
            "metrics_summary_json": json.dumps(metrics),
        }
