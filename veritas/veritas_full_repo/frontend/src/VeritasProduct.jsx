import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  connectHpc,
  fetchHpcSummary,
  fetchPipelines,
  previewSlurmJob,
  submitSlurmJob,
  testHpcConnection,
} from "./api/veritasClient.js";
import { isVeritasApiConfigured } from "./config.js";

const COLORS = {
  navy: "#0f2f6b",
  navySoft: "#eaf1fb",
  line: "#d7e2f2",
  text: "#16325c",
  muted: "#5e7394",
  bg: "#f6f9fe",
  soft: "#f8fbff",
};

const NAV_ITEMS = [
  { id: "home", label: "Home" },
  { id: "user", label: "User Dashboard" },
  { id: "pipeline", label: "Pipeline" },
  { id: "leaderboard", label: "Leaderboard" },
  { id: "atlas_api", label: "Atlas API access" },
  { id: "atlas_admin", label: "Atlas admin" },
  { id: "admin", label: "Veritas admin" },
];

const INITIAL_API_INQUIRIES = [
  {
    id: "API-DEMO-001",
    submittedAt: "2026-03-10 14:22",
    full_name: "Dr. Alex Chen",
    email: "alex.chen@hospital.org",
    institution: "Clinical AI Group",
    role_title: "PI",
    dataset_interest: "HS Dataset",
    use_case: "Batch sync of public cohort metadata for an internal benchmarking study.",
    status: "pending",
  },
  {
    id: "API-DEMO-002",
    submittedAt: "2026-03-08 09:05",
    full_name: "Sam Rivera",
    email: "s.rivera@university.edu",
    institution: "University Lab",
    role_title: "Research engineer",
    dataset_interest: "FCD Dataset",
    use_case: "REST access for automated pipeline validation against restricted cohort (IRB in place).",
    status: "approved",
  },
];

function newApiInquiryId() {
  return `API-${Date.now().toString(36).toUpperCase()}`;
}

function formatInquiryTimestamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const USER_PHASES = ["Pipeline Prep", "Data Prep", "Processing", "Reporting", "Completed"];
const ADMIN_PHASES = ["Pipeline Prep", "Data Prep", "Processing", "Reporting", "Completed"];
const SLURM_PRESETS = [
  "1 GPU • 8 CPU • 32 GB RAM",
  "1 GPU • 16 CPU • 64 GB RAM",
  "2 GPU • 24 CPU • 128 GB RAM",
  "CPU Only • 16 CPU • 64 GB RAM",
];

/** Maps admin Slurm form fields to POST /jobs/preview|submit JSON (SlurmJobSubmitRequest). */
function buildSlurmSubmitPayload(slurmForm) {
  const gpu = parseInt(String(slurmForm.gpus), 10);
  const cpu = parseInt(String(slurmForm.cpus), 10);
  const mem = parseInt(String(slurmForm.memory_gb), 10);
  const rp = (slurmForm.runtime_profile || "generic").trim().toLowerCase();
  const payload = {
    job_name: slurmForm.job_name.trim(),
    pipeline: slurmForm.pipeline_image.trim(),
    dataset: slurmForm.dataset.trim(),
    partition: (slurmForm.partition || "gpu").trim(),
    resources: {
      preset: slurmForm.resources || null,
      gpu: Number.isFinite(gpu) && gpu > 0 ? gpu : 1,
      cpu: Number.isFinite(cpu) && cpu > 0 ? cpu : 16,
      memory_gb: Number.isFinite(mem) && mem > 0 ? mem : 64,
      wall_time: (slurmForm.wall_time || "08:00:00").trim(),
      constraint: slurmForm.constraint.trim() || null,
      sbatch_overrides: slurmForm.sbatch_overrides.trim() || null,
    },
    runtime_profile: rp === "meld_graph" ? "meld_graph" : "generic",
  };
  const pn = slurmForm.pipeline_name.trim();
  if (pn) payload.pipeline_name = pn;
  if (rp === "meld_graph") {
    const sid = slurmForm.meld_subject_id.trim();
    if (sid) payload.meld_subject_id = sid;
  }
  return payload;
}

function buildHpcConnectPayload(hpcForm) {
  const port = parseInt(String(hpcForm.port), 10);
  const kp = (hpcForm.key_path || "").trim();
  return {
    hostname: (hpcForm.hostname || "").trim(),
    username: (hpcForm.username || "").trim(),
    port: Number.isFinite(port) && port > 0 ? port : 22,
    key_path: kp || null,
    notes: (hpcForm.notes || "").trim() || null,
  };
}

const DATASETS = [
  { name: "HS Dataset", disease: "Epilepsy", biomarker: "HS", code: "ATLAS-HS-1", version: "v1", subjects: 212, source: "Atlas / Pennsieve", qc: "validated" },
  { name: "FCD Dataset", disease: "Epilepsy", biomarker: "FCD", code: "ATLAS-FCD-1", version: "v2", subjects: 184, source: "Atlas / Pennsieve", qc: "validated" },
  { name: "Alzheimer Dataset", disease: "Alzheimer", biomarker: "AD", code: "ATLAS-AD-1", version: "v3", subjects: 420, source: "Atlas / Pennsieve", qc: "validated" },
  { name: "TSC Dataset", disease: "TSC", biomarker: "TSC", code: "ATLAS-TSC-1", version: "v1", subjects: 96, source: "Atlas / Pennsieve", qc: "pilot" },
  { name: "Epilepsy Dataset", disease: "Epilepsy", biomarker: "General", code: "ATLAS-EPI-1", version: "v1", subjects: 510, source: "Atlas / Pennsieve", qc: "validated" },
  { name: "ideas (IDEAS)", disease: "Epilepsy", biomarker: "FCD / MELD", code: "IDEAS", version: "v1", subjects: 0, source: "Atlas (public)", qc: "validated" },
];

const REQUESTS = [
  {
    id: "REQ-1042",
    user: "Dr. Allen",
    requesterEmail: "allen@hospital.org",
    datasets: "HS Dataset",
    pipeline: "registry/org/hsnet:1.0",
    phase: "Processing",
    report: "Generating",
    submitted: "2026-03-12 09:20",
    admin_note: "Atlas staging validated. Hidden test run in progress.",
    atlasId: "ATLAS-HS-1",
    approval: "approved",
    staging: "validated",
    hiddenTest: "evaluated",
    bundle: "EVB-REQ-1042",
  },
  {
    id: "REQ-1043",
    user: "Dr. Rivera",
    requesterEmail: "rivera@university.edu",
    datasets: "FCD Dataset",
    pipeline: "registry/org/fcdgraph:2.1",
    phase: "Reporting",
    report: "Ready",
    submitted: "2026-03-12 10:05",
    admin_note: "Report generated and eligible for leaderboard push.",
    atlasId: "ATLAS-FCD-1",
    approval: "approved",
    staging: "validated",
    hiddenTest: "evaluated",
    bundle: "EVB-REQ-1043",
  },
  {
    id: "REQ-1044",
    user: "Dr. Shah",
    requesterEmail: "shah@research.org",
    datasets: "Alzheimer Dataset",
    pipeline: "registry/org/ad-biomarker:0.9",
    phase: "Data Prep",
    report: "Not Ready",
    submitted: "2026-03-12 11:12",
    admin_note: "Awaiting Atlas approval for staging.",
    atlasId: "ATLAS-AD-1",
    approval: "pending",
    staging: "not_started",
    hiddenTest: "not_started",
    bundle: "—",
  },
  {
    id: "REQ-1045",
    user: "Dr. Kim",
    requesterEmail: "kim@neuro.edu",
    datasets: "ideas (IDEAS)",
    pipeline: "docker.io/meldproject/meld_graph:latest",
    phase: "Pipeline Prep",
    report: "Not Ready",
    submitted: "2026-03-14 08:00",
    admin_note: "Veritas catalog: meld-graph-fcd + Atlas dataset_id ideas; staging via POST /atlas/staging/request.",
    atlasId: "ideas",
    approval: "approved",
    staging: "validated",
    hiddenTest: "not_started",
    bundle: "EVB-REQ-1045",
  },
];

const LEADERBOARD = {
  HS: [
    { rank: 1, pipeline: "HSNet", dataset: "HS Dataset", score: 0.85, metric: "Overall Score", published: "2026-03-12" },
    { rank: 2, pipeline: "HippoGraph", dataset: "HS Dataset", score: 0.82, metric: "Overall Score", published: "2026-03-10" },
  ],
  FCD: [
    { rank: 1, pipeline: "FCDGraph", dataset: "FCD Dataset", score: 0.82, metric: "Overall Score", published: "2026-03-11" },
    { rank: 2, pipeline: "LesionNet", dataset: "FCD Dataset", score: 0.79, metric: "Overall Score", published: "2026-03-08" },
  ],
  AD: [
    { rank: 1, pipeline: "AD-Biomarker", dataset: "Alzheimer Dataset", score: 0.88, metric: "Overall Score", published: "2026-03-09" },
  ],
};

const JOBS = [
  { id: "JOB-801", requestId: "REQ-1042", status: "Running", type: "Hidden Test Eval", updatedAt: "11:48", schedulerId: "57291", lastSync: "11:49", workdir: "/scratch/veritas/REQ-1042", stdout: "stdout.log", stderr: "stderr.log" },
  { id: "JOB-802", requestId: "REQ-1043", status: "Completed", type: "Report Generation", updatedAt: "11:25", schedulerId: "57284", lastSync: "11:30", workdir: "/scratch/veritas/REQ-1043", stdout: "stdout.log", stderr: "stderr.log" },
];

const ARTIFACTS = [
  { id: "A1", name: "report.pdf", type: "PDF", status: "Ready", size: "1.2 MB" },
  { id: "A2", name: "metrics.json", type: "JSON", status: "Ready", size: "4 KB" },
  { id: "A3", name: "results.csv", type: "CSV", status: "Ready", size: "24 KB" },
  { id: "A4", name: "stdout.log", type: "LOG", status: "Ready", size: "18 KB" },
];

const METRICS = [
  ["Dice", "0.83"],
  ["Sensitivity", "0.79"],
  ["Specificity", "0.91"],
  ["AUC", "0.88"],
  ["Precision", "0.84"],
  ["F1 Score", "0.81"],
];

const RUNTIME = [
  ["Runtime Engine", "Apptainer"],
  ["Partition", "gpu"],
  ["GPUs", "1"],
  ["CPUs", "16"],
  ["Memory", "64 GB"],
  ["Generated", "2026-03-12 11:30"],
  ["Published", "2026-03-12 11:34"],
];

function Card({ children, className = "" }) {
  return <div className={`rounded-3xl border bg-white shadow-sm ${className}`} style={{ borderColor: COLORS.line }}>{children}</div>;
}

function PageShell({ children }) {
  return <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</div>;
}

function SectionTitle({ title, subtitle }) {
  return (
    <div className="mb-6">
      <h2 className="text-2xl font-semibold sm:text-3xl" style={{ color: COLORS.text }}>{title}</h2>
      {subtitle ? <p className="mt-2 max-w-2xl text-sm sm:text-base" style={{ color: COLORS.muted }}>{subtitle}</p> : null}
    </div>
  );
}

function SmallStat({ value, label }) {
  return (
    <div className="rounded-2xl bg-white p-3 text-center">
      <div className="text-xl font-semibold" style={{ color: COLORS.navy }}>{value}</div>
      <div className="mt-1 text-xs" style={{ color: COLORS.muted }}>{label}</div>
    </div>
  );
}

function StatusText({ message, error = false }) {
  if (!message) return null;
  return <div className="text-sm" style={{ color: error ? "#b91c1c" : COLORS.muted }}>{message}</div>;
}

function ModalShell({ title, subtitle, onClose, children, footer, panelClassName = "max-w-2xl" }) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/40 px-4">
      <div className={`w-full ${panelClassName} max-h-[92vh] overflow-y-auto rounded-3xl border bg-white p-6 shadow-2xl`} style={{ borderColor: COLORS.line }}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-xl font-semibold" style={{ color: COLORS.text }}>{title}</h3>
            {subtitle ? <p className="mt-1 text-sm" style={{ color: COLORS.muted }}>{subtitle}</p> : null}
          </div>
          <button onClick={onClose} className="rounded-full border px-3 py-1 text-sm" style={{ borderColor: COLORS.line, color: COLORS.text }}>Close</button>
        </div>
        <div className="mt-5">{children}</div>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end">{footer}</div>
      </div>
    </div>
  );
}

function ScrollList({ title, items, selected, onSelect }) {
  return (
    <div className="rounded-2xl border bg-white p-3" style={{ borderColor: COLORS.line }}>
      <div className="mb-2 text-xs font-medium uppercase tracking-wide" style={{ color: COLORS.muted }}>{title}</div>
      <div className="max-h-40 space-y-2 overflow-y-auto pr-1">
        {items.map((item) => {
          const label = typeof item === "string" ? item : item.name;
          const active = selected === label;
          return (
            <button
              key={label}
              onClick={() => onSelect(label)}
              className="w-full rounded-xl border px-3 py-2 text-left text-sm"
              style={{
                borderColor: active ? "#bfdbfe" : COLORS.line,
                backgroundColor: active ? "#eff6ff" : "#ffffff",
                color: COLORS.text,
              }}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function TextField({ label, placeholder, value, onChange, className = "", textarea = false }) {
  const base = `w-full rounded-2xl border bg-white px-4 py-3 text-sm outline-none ${className}`;
  return (
    <div>
      <label className="mb-2 block text-sm" style={{ color: COLORS.muted }}>{label}</label>
      {textarea ? (
        <textarea className={base} style={{ borderColor: COLORS.line, color: COLORS.text }} placeholder={placeholder} value={value} onChange={onChange} />
      ) : (
        <input className={base} style={{ borderColor: COLORS.line, color: COLORS.text }} placeholder={placeholder} value={value} onChange={onChange} />
      )}
    </div>
  );
}

function SelectField({ label, options, value, onChange, className = "" }) {
  return (
    <div>
      <label className="mb-2 block text-sm" style={{ color: COLORS.muted }}>{label}</label>
      <select className={`w-full rounded-xl border bg-white px-3 py-2 text-sm outline-none ${className}`} style={{ borderColor: COLORS.line, color: COLORS.text }} value={value} onChange={onChange}>
        {options.map((option) => {
          const optionValue = typeof option === "string" ? option : option.name;
          return <option key={optionValue} value={optionValue}>{optionValue}</option>;
        })}
      </select>
    </div>
  );
}

function Pill({ label, active = false, complete = false }) {
  return (
    <div
      className="rounded-full border px-3 py-1 text-xs font-medium sm:text-sm"
      style={{
        borderColor: active ? "#bfdbfe" : COLORS.line,
        backgroundColor: active ? "#dbeafe" : complete ? "#f1f5f9" : "#ffffff",
        color: active ? "#1e3a8a" : complete ? "#475569" : "#64748b",
      }}
    >
      {complete ? "✓" : active ? "●" : "○"} {label}
    </div>
  );
}

export default function VeritasApp() {
  const [page, setPage] = useState("home");
  const [showHpcModal, setShowHpcModal] = useState(false);
  const [showSlurmModal, setShowSlurmModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [hpcSummary, setHpcSummary] = useState(null);
  const [hpcSummaryLoading, setHpcSummaryLoading] = useState(false);
  const [hpcSummaryError, setHpcSummaryError] = useState(null);
  const [hpcModalBusy, setHpcModalBusy] = useState(false);
  const [hpcModalMessage, setHpcModalMessage] = useState(null);
  const [submitJobLoading, setSubmitJobLoading] = useState(false);
  const [pipelineTemplate, setPipelineTemplate] = useState("meld_graph");
  const [reportStatus, setReportStatus] = useState(null);
  const [requests, setRequests] = useState(REQUESTS);
  const [selectedRequestId, setSelectedRequestId] = useState(REQUESTS[0].id);
  const selectedRequest = useMemo(
    () => requests.find((r) => r.id === selectedRequestId) ?? requests[0],
    [requests, selectedRequestId],
  );
  const [selectedDataset, setSelectedDataset] = useState(DATASETS[0].name);
  const [selectedPipeline, setSelectedPipeline] = useState("registry/org/hsnet:1.0");
  const [requestForm, setRequestForm] = useState({ dataset: DATASETS[0].name, pipeline: "registry/org/model:1.0", description: "Evaluate hippocampal sclerosis biomarker pipeline." });
  const [pipelineDraft, setPipelineDraft] = useState({
    name: "my-biomarker",
    title: "My biomarker pipeline",
    image: "docker.io/phindagijimana321/my-biomarker:v1",
    modality: "MRI",
    entrypoint: "python /app/run.py --input /input --output /output",
    description: "Built from your Dockerfile, pushed to Docker Hub, then referenced here for Slurm jobs.",
  });
  const [hpcForm, setHpcForm] = useState({ hostname: "hpc.example.org", username: "researcher", port: "22", key_path: "~/.ssh/id_rsa", notes: "OOD login available" });
  const [slurmForm, setSlurmForm] = useState({
    job_name: "biomarker-eval-job",
    resources: SLURM_PRESETS[1],
    partition: "gpu",
    gpus: "1",
    cpus: "16",
    memory_gb: "64",
    wall_time: "08:00:00",
    constraint: "a100",
    sbatch_overrides: "#SBATCH --gres=gpu:1\n#SBATCH --cpus-per-task=16\n#SBATCH --mem=64G",
    dataset: "ideas",
    pipeline_image: "docker.io/meldproject/meld_graph:latest",
    pipeline_name: "meld-graph-fcd",
    runtime_profile: "generic",
    meld_subject_id: "",
  });
  const [jobPreview, setJobPreview] = useState({ loading: false, error: null, data: null });
  const [slurmPreviewTab, setSlurmPreviewTab] = useState("sbatch");
  const [adminNote, setAdminNote] = useState(REQUESTS[0].admin_note);
  const [reportForm, setReportForm] = useState({ subject: "", body: "" });
  const [pipelinesLive, setPipelinesLive] = useState(null);

  useEffect(() => {
    setAdminNote(selectedRequest.admin_note);
  }, [selectedRequest]);

  useEffect(() => {
    if (page !== "pipeline" || !isVeritasApiConfigured()) return;
    let cancelled = false;
    fetchPipelines().then((j) => {
      if (cancelled || !j?.data) return;
      setPipelinesLive(Array.isArray(j.data) ? j.data : []);
    });
    return () => {
      cancelled = true;
    };
  }, [page]);
  const [atlasApiForm, setAtlasApiForm] = useState({
    full_name: "",
    email: "",
    institution: "",
    role_title: "",
    dataset_interest: DATASETS[0].name,
    use_case: "",
  });
  const [atlasApiStatus, setAtlasApiStatus] = useState(null);
  const [apiInquiries, setApiInquiries] = useState(() => [...INITIAL_API_INQUIRIES]);
  const [selectedInquiryId, setSelectedInquiryId] = useState(INITIAL_API_INQUIRIES[0]?.id ?? null);
  const [inquiryFilter, setInquiryFilter] = useState("all");

  const selectedDatasetInfo = useMemo(() => DATASETS.find((d) => d.name === selectedDataset) || DATASETS[0], [selectedDataset]);
  const filteredInquiries = useMemo(() => {
    if (inquiryFilter === "all") return apiInquiries;
    return apiInquiries.filter((r) => r.status === inquiryFilter);
  }, [apiInquiries, inquiryFilter]);
  const selectedInquiry = useMemo(
    () => apiInquiries.find((r) => r.id === selectedInquiryId) ?? null,
    [apiInquiries, selectedInquiryId],
  );
  const phaseIndex = USER_PHASES.indexOf(selectedRequest.phase);

  const activeHpc = useMemo(() => hpcSummary?.active_connection?.status === "connected", [hpcSummary]);
  const slurmSubmitBlocked = useMemo(() => hpcSummary?.hpc_mode === "slurm" && !activeHpc, [hpcSummary, activeHpc]);

  const pipelineYamlPreview = useMemo(() => {
    if (pipelineTemplate === "meld_graph") {
      const n = pipelineDraft.name || "meld-graph-fcd";
      return `# MELD Graph — register via POST /api/v1/pipelines (operators curate YAML after your request).
# Licenses: host directory with license.txt (FreeSurfer) + meld_license.txt (MELD); set MELD_LICENSE_HOST_DIR on the API/compute nodes.
# Inputs: BIDS dataset (e.g. IDEAS) staged to the cluster; T1w anat per meld_bids_config.
# Outputs: lesion predictions and metrics under the job artifact layout.
name: ${n}
title: ${pipelineDraft.title || "MELD Graph FCD (T1w)"}
image: ${pipelineDraft.image || "docker.io/meldproject/meld_graph:latest"}
modality: MRI
entrypoint: python scripts/new_patient_pipeline/new_pt_pipeline.py
inputs:
  - name: bids_t1
    type: BIDS
outputs:
  - name: predictions
    type: directory
resources:
  cpu: 16
runtime_profile: meld_graph
atlas_dataset_id: ideas
plugin:
  type: meld_graph
  containers:
    freesurfer: docker.io/freesurfer/freesurfer:7.4.1
    meld: docker.io/meldproject/meld_graph:latest
  secrets:
    freesurfer_license_file: license.txt
    meld_license_file: meld_license.txt
  container_env:
    FS_LICENSE: /run/secrets/license.txt
    MELD_LICENSE: /run/secrets/meld_license.txt`;
    }
    const n = pipelineDraft.name || "my-pipeline";
    return `name: ${n}
title: ${pipelineDraft.title || n}
image: ${pipelineDraft.image}
modality: ${pipelineDraft.modality || "MRI"}
entrypoint: ${pipelineDraft.entrypoint || "python /app/run.py"}
inputs:
  - name: study_input
    type: directory
outputs:
  - name: metrics
    type: json
  - name: predictions
    type: directory
resources:
  cpu: 8
reports:
  - name: benchmark_report
    type: pdf
    description: Sent to the requester with email notification
  - name: metrics_json
    type: json`;
  }, [pipelineDraft, pipelineTemplate]);

  const refreshHpcSummary = useCallback(async () => {
    if (!isVeritasApiConfigured()) return;
    setHpcSummaryLoading(true);
    setHpcSummaryError(null);
    const res = await fetchHpcSummary();
    setHpcSummaryLoading(false);
    if (res.ok) setHpcSummary(res.data);
    else setHpcSummaryError(res.message);
  }, []);

  useEffect(() => {
    if (page !== "admin" || !isVeritasApiConfigured()) return;
    let cancelled = false;
    (async () => {
      setHpcSummaryLoading(true);
      setHpcSummaryError(null);
      const res = await fetchHpcSummary();
      if (cancelled) return;
      setHpcSummaryLoading(false);
      if (res.ok) setHpcSummary(res.data);
      else setHpcSummaryError(res.message);
    })();
    return () => {
      cancelled = true;
    };
  }, [page]);

  const navButton = (item, mobile = false) => {
    const active = page === item.id;
    return (
      <button
        key={item.id}
        onClick={() => setPage(item.id)}
        className={`rounded-full px-4 py-2 text-sm font-medium transition ${mobile ? "w-full text-left" : ""}`}
        style={{
          backgroundColor: active ? (mobile ? COLORS.navy : "#ffffff") : mobile ? "#ffffff" : "transparent",
          color: active ? (mobile ? "#ffffff" : COLORS.navy) : mobile ? COLORS.text : "rgba(255,255,255,0.9)",
        }}
      >
        {item.label}
      </button>
    );
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: COLORS.bg }}>
      <div className="sticky top-0 z-50 border-b" style={{ backgroundColor: COLORS.navy, borderColor: "rgba(255,255,255,0.08)" }}>
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
          <div className="flex items-center justify-between gap-4">
            <button
              type="button"
              onClick={() => setPage("home")}
              className="flex min-w-0 items-center gap-3 text-left"
              style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
            >
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/25 bg-white/10 shadow-inner"
                aria-hidden
              >
                <span
                  className="select-none text-[1.35rem] font-bold leading-none tracking-tight text-white"
                  style={{ fontFamily: "Georgia, 'Times New Roman', ui-serif, serif" }}
                >
                  V
                </span>
              </div>
              <div className="min-w-0 text-left">
                <div className="truncate font-semibold tracking-wide text-white">Veritas</div>
                <div className="hidden text-xs sm:block" style={{ color: "rgba(219,234,254,0.8)" }}>AI biomarker validation platform</div>
              </div>
            </button>
            <div className="hidden items-center gap-1 rounded-full border p-1 lg:flex" style={{ borderColor: "rgba(255,255,255,0.15)", backgroundColor: "rgba(255,255,255,0.05)" }}>
              {NAV_ITEMS.map((item) => navButton(item))}
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 lg:hidden" style={{ borderColor: "rgba(255,255,255,0.12)" }}>
            {NAV_ITEMS.map((item) => navButton(item, true))}
          </div>
        </div>
      </div>

      {page === "home" && (
        <PageShell>
          <Card className="p-6 sm:p-8 lg:p-10">
            <h1 className="max-w-3xl text-3xl font-semibold leading-tight sm:text-4xl lg:text-5xl" style={{ color: COLORS.text }}>
              Veritas validates AI biomarker pipelines on curated datasets.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-relaxed sm:text-lg" style={{ color: COLORS.muted }}>
              Submit packaged pipelines, track evaluation updates, and receive standardized benchmark reports.
            </p>
            <div className="mt-6 grid gap-3">
              {[
                "Clinical and open dataset evaluation housed in Atlas API",
                "Secure execution on HPC",
                "Standardized report delivery",
                "Hidden test evaluation for benchmark integrity",
              ].map((item) => (
                <div key={item} className="flex items-center gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border text-sm font-semibold" style={{ borderColor: COLORS.line, backgroundColor: COLORS.navySoft, color: COLORS.navy }}>✓</div>
                  <div className="text-sm sm:text-base" style={{ color: COLORS.text }}>{item}</div>
                </div>
              ))}
            </div>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <button type="button" onClick={() => setPage("user")} className="rounded-full px-5 py-3 font-medium text-white" style={{ backgroundColor: COLORS.navy }}>Go to User Dashboard</button>
              <button type="button" onClick={() => setPage("admin")} className="rounded-full border px-5 py-3 font-medium" style={{ borderColor: COLORS.line, color: COLORS.navy }}>Open Veritas admin</button>
              <button type="button" onClick={() => setPage("atlas_admin")} className="rounded-full border px-5 py-3 font-medium" style={{ borderColor: COLORS.line, color: COLORS.navy }}>Atlas admin (API requests)</button>
              <button type="button" onClick={() => setPage("atlas_api")} className="rounded-full border border-dashed px-5 py-3 font-medium" style={{ borderColor: COLORS.line, color: COLORS.muted }}>Request Atlas API access</button>
            </div>
          </Card>
        </PageShell>
      )}

      {page === "atlas_api" && (
        <PageShell>
          <SectionTitle
            title="Atlas API access"
            subtitle="Request credentials for the Atlas dataset API if your workflow needs programmatic discovery, metadata, or downloads. Access follows Atlas data policies (public, restricted, private). Veritas operators route requests to the same Atlas service."
          />
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="p-6 lg:col-span-2">
              {atlasApiStatus === "sent" ? (
                <div className="rounded-2xl border p-8 text-center" style={{ borderColor: COLORS.line, backgroundColor: COLORS.navySoft }}>
                  <p className="text-lg font-semibold" style={{ color: COLORS.text }}>Thanks — your request was recorded</p>
                  <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed" style={{ color: COLORS.muted }}>
                    It now appears under <strong style={{ color: COLORS.text }}>Atlas admin</strong> for your operators. In production, persist via your API (e.g.{" "}
                    <code className="rounded bg-white px-1 py-0.5 text-xs" style={{ color: COLORS.navy }}>POST /api/v1/access-requests</code>
                    ).
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        setAtlasApiStatus(null);
                        setAtlasApiForm({
                          full_name: "",
                          email: "",
                          institution: "",
                          role_title: "",
                          dataset_interest: DATASETS[0].name,
                          use_case: "",
                        });
                      }}
                      className="rounded-full border px-5 py-2.5 text-sm font-medium"
                      style={{ borderColor: COLORS.line, color: COLORS.navy }}
                    >
                      Submit another
                    </button>
                    <button
                      type="button"
                      onClick={() => setPage("home")}
                      className="rounded-full px-5 py-2.5 text-sm font-medium text-white"
                      style={{ backgroundColor: COLORS.navy }}
                    >
                      Back to home
                    </button>
                  </div>
                </div>
              ) : (
                <form
                  className="grid gap-5"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!atlasApiForm.email.trim() || !atlasApiForm.full_name.trim() || !atlasApiForm.use_case.trim()) {
                      return;
                    }
                    const id = newApiInquiryId();
                    const row = {
                      id,
                      submittedAt: formatInquiryTimestamp(),
                      full_name: atlasApiForm.full_name.trim(),
                      email: atlasApiForm.email.trim(),
                      institution: atlasApiForm.institution.trim(),
                      role_title: atlasApiForm.role_title.trim(),
                      dataset_interest: atlasApiForm.dataset_interest,
                      use_case: atlasApiForm.use_case.trim(),
                      status: "pending",
                    };
                    setApiInquiries((prev) => [row, ...prev]);
                    setSelectedInquiryId(id);
                    setAtlasApiStatus("sent");
                  }}
                >
                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField
                      label="Full name"
                      placeholder="Dr. Jane Smith"
                      value={atlasApiForm.full_name}
                      onChange={(e) => setAtlasApiForm({ ...atlasApiForm, full_name: e.target.value })}
                    />
                    <TextField
                      label="Work email"
                      placeholder="you@institution.org"
                      value={atlasApiForm.email}
                      onChange={(e) => setAtlasApiForm({ ...atlasApiForm, email: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField
                      label="Institution or lab"
                      placeholder="University / hospital / company"
                      value={atlasApiForm.institution}
                      onChange={(e) => setAtlasApiForm({ ...atlasApiForm, institution: e.target.value })}
                    />
                    <TextField
                      label="Role"
                      placeholder="PI, engineer, analyst…"
                      value={atlasApiForm.role_title}
                      onChange={(e) => setAtlasApiForm({ ...atlasApiForm, role_title: e.target.value })}
                    />
                  </div>
                  <SelectField
                    label="Primary dataset interest (optional)"
                    options={DATASETS}
                    value={atlasApiForm.dataset_interest}
                    onChange={(e) => setAtlasApiForm({ ...atlasApiForm, dataset_interest: e.target.value })}
                  />
                  <TextField
                    label="Describe how you will use the API"
                    placeholder="e.g. Automated nightly sync of public cohort metadata; benchmarking pipeline against restricted cohort with IRB…"
                    textarea
                    className="min-h-[120px]"
                    value={atlasApiForm.use_case}
                    onChange={(e) => setAtlasApiForm({ ...atlasApiForm, use_case: e.target.value })}
                  />
                  <p className="text-xs leading-relaxed" style={{ color: COLORS.muted }}>
                    By submitting, you confirm the use case is accurate. Restricted data may require additional agreements
                    before credentials are issued.
                  </p>
                  <div className="flex flex-wrap gap-3">
                    <button type="submit" className="rounded-full px-6 py-3 text-sm font-medium text-white" style={{ backgroundColor: COLORS.navy }}>
                      Submit request
                    </button>
                    <button
                      type="button"
                      onClick={() => setPage("home")}
                      className="rounded-full border px-6 py-3 text-sm font-medium"
                      style={{ borderColor: COLORS.line, color: COLORS.muted }}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </Card>
            <Card className="h-fit p-5">
              <h3 className="text-xs font-semibold uppercase tracking-wide" style={{ color: COLORS.muted }}>
                About Atlas API access
              </h3>
              <ul className="mt-4 space-y-3 text-sm leading-relaxed" style={{ color: COLORS.text }}>
                <li className="flex gap-2">
                  <span className="shrink-0 font-semibold" style={{ color: COLORS.navy }}>•</span>
                  <span>Use this page when you need API keys or OAuth client setup beyond the Veritas web UI.</span>
                </li>
                <li className="flex gap-2">
                  <span className="shrink-0 font-semibold" style={{ color: COLORS.navy }}>•</span>
                  <span>Public datasets may be approved quickly; restricted cohorts need policy review.</span>
                </li>
                <li className="flex gap-2">
                  <span className="shrink-0 font-semibold" style={{ color: COLORS.navy }}>•</span>
                  <span>Veritas validation jobs still consume Atlas through the platform; this form is for direct API consumers.</span>
                </li>
              </ul>
            </Card>
          </div>
        </PageShell>
      )}

      {page === "atlas_admin" && (
        <PageShell>
          <SectionTitle
            title="Atlas admin"
            subtitle="Review Atlas API access inquiries submitted from the Atlas API access page. Approve or decline after policy review; wire this list to your backend for persistence."
          />
          <div className="mb-4 flex flex-wrap gap-2">
            {["all", "pending", "approved", "declined"].map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setInquiryFilter(f)}
                className="rounded-full border px-4 py-1.5 text-sm font-medium capitalize"
                style={{
                  borderColor: inquiryFilter === f ? COLORS.navy : COLORS.line,
                  backgroundColor: inquiryFilter === f ? COLORS.navySoft : "#fff",
                  color: inquiryFilter === f ? COLORS.navy : COLORS.muted,
                }}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="grid gap-6 lg:grid-cols-5">
            <Card className="overflow-hidden lg:col-span-3">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead style={{ backgroundColor: COLORS.navySoft, color: COLORS.text }}>
                    <tr>
                      {["ID", "Submitted", "Requester", "Dataset", "Status"].map((h) => (
                        <th key={h} className="px-4 py-3 font-medium">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredInquiries.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center" style={{ color: COLORS.muted }}>
                          No inquiries in this filter.
                        </td>
                      </tr>
                    ) : (
                      filteredInquiries.map((row, idx) => (
                        <tr
                          key={row.id}
                          className={idx < filteredInquiries.length - 1 ? "border-t" : ""}
                          style={{ borderColor: COLORS.line, cursor: "pointer", backgroundColor: selectedInquiryId === row.id ? "#f1f5f9" : undefined }}
                          onClick={() => setSelectedInquiryId(row.id)}
                        >
                          <td className="px-4 py-3 font-mono text-xs" style={{ color: COLORS.navy }}>
                            {row.id}
                          </td>
                          <td className="px-4 py-3" style={{ color: COLORS.muted }}>
                            {row.submittedAt}
                          </td>
                          <td className="px-4 py-3" style={{ color: COLORS.text }}>
                            {row.full_name}
                            <div className="text-xs" style={{ color: COLORS.muted }}>
                              {row.email}
                            </div>
                          </td>
                          <td className="px-4 py-3" style={{ color: COLORS.muted }}>
                            {row.dataset_interest}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className="rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize"
                              style={{
                                borderColor: COLORS.line,
                                backgroundColor:
                                  row.status === "approved" ? "#ecfdf3" : row.status === "declined" ? "#fef2f2" : COLORS.soft,
                                color: row.status === "approved" ? "#166534" : row.status === "declined" ? "#b91c1c" : COLORS.text,
                              }}
                            >
                              {row.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
            <Card className="h-fit p-5 lg:col-span-2">
              <h3 className="text-sm font-semibold uppercase tracking-wide" style={{ color: COLORS.muted }}>
                Inquiry detail
              </h3>
              {selectedInquiry ? (
                <div className="mt-4 space-y-3 text-sm">
                  <div>
                    <span style={{ color: COLORS.muted }}>ID</span>
                    <div className="font-mono text-xs" style={{ color: COLORS.navy }}>
                      {selectedInquiry.id}
                    </div>
                  </div>
                  <div>
                    <span style={{ color: COLORS.muted }}>Institution / role</span>
                    <div style={{ color: COLORS.text }}>
                      {selectedInquiry.institution || "—"} · {selectedInquiry.role_title || "—"}
                    </div>
                  </div>
                  <div>
                    <span style={{ color: COLORS.muted }}>Use case</span>
                    <p className="mt-1 leading-relaxed" style={{ color: COLORS.text }}>
                      {selectedInquiry.use_case}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 pt-2">
                    <button
                      type="button"
                      disabled={selectedInquiry.status !== "pending"}
                      onClick={() => {
                        setApiInquiries((prev) =>
                          prev.map((r) => (r.id === selectedInquiry.id ? { ...r, status: "approved" } : r)),
                        );
                      }}
                      className="rounded-full px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
                      style={{ backgroundColor: "#166534" }}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      disabled={selectedInquiry.status !== "pending"}
                      onClick={() => {
                        setApiInquiries((prev) =>
                          prev.map((r) => (r.id === selectedInquiry.id ? { ...r, status: "declined" } : r)),
                        );
                      }}
                      className="rounded-full border px-4 py-2 text-sm font-medium disabled:opacity-40"
                      style={{ borderColor: COLORS.line, color: "#b91c1c" }}
                    >
                      Decline
                    </button>
                  </div>
                </div>
              ) : (
                <p className="mt-4 text-sm" style={{ color: COLORS.muted }}>
                  Select a row to review the full request.
                </p>
              )}
            </Card>
          </div>
        </PageShell>
      )}

      {page === "user" && (
        <PageShell>
          <SectionTitle
            title="User Dashboard"
            subtitle="Submit your packaged pipeline (container image). For MELD on IDEAS, include the image reference you pushed; operators will attach YAML (inputs, outputs, licenses) and run validation on HPC after you are approved."
          />
          <div className="grid gap-5 xl:grid-cols-12 items-stretch">
            <Card className="p-5 sm:p-6 xl:col-span-7">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-lg font-semibold sm:text-xl" style={{ color: COLORS.text }}>Submit Request</h3>
                  <p className="mt-1 text-sm" style={{ color: COLORS.muted }}>References the Docker/OCI image Veritas will pull on the cluster (Apptainer/Singularity or Docker per site policy).</p>
                </div>
                <div className="w-fit rounded-full border px-4 py-2 text-sm" style={{ borderColor: COLORS.line, backgroundColor: COLORS.soft, color: COLORS.text }}>User ▾</div>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <SelectField label="Dataset" options={DATASETS} value={requestForm.dataset} onChange={(e) => { setRequestForm({ ...requestForm, dataset: e.target.value }); setSelectedDataset(e.target.value); }} className="lg:col-span-2" />
                <TextField label="Packaged Pipeline" placeholder="docker.io/meldproject/meld_graph:latest" value={requestForm.pipeline} onChange={(e) => setRequestForm({ ...requestForm, pipeline: e.target.value })} className="lg:col-span-2" />
                <TextField label="Description" placeholder="Brief purpose / hypothesis" textarea className="min-h-[110px] lg:col-span-2" value={requestForm.description} onChange={(e) => setRequestForm({ ...requestForm, description: e.target.value })} />
              </div>
            </Card>
            <Card className="p-5 sm:p-6 xl:col-span-5">
              <h3 className="text-lg font-semibold sm:text-xl" style={{ color: COLORS.text }}>Selected Request</h3>
              <div className="mt-4 flex flex-wrap gap-2">
                {USER_PHASES.map((label, i) => <Pill key={label} label={label} active={i === phaseIndex} complete={i < phaseIndex} />)}
              </div>
            </Card>
            <Card className="p-5 sm:p-6 xl:col-span-12">
              <h3 className="text-base font-semibold" style={{ color: COLORS.text }}>MELD Graph (example)</h3>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed" style={{ color: COLORS.muted }}>
                <li><span style={{ color: COLORS.text }}>Container:</span> e.g. <code className="rounded bg-slate-100 px-1 text-xs">docker.io/meldproject/meld_graph:latest</code> (plus FreeSurfer sidecar in YAML).</li>
                <li><span style={{ color: COLORS.text }}>Inputs:</span> BIDS dataset with T1w anatomical; IDEAS cohort uses dataset id <code className="rounded bg-slate-100 px-1 text-xs">ideas</code> and staging to the cluster.</li>
                <li><span style={{ color: COLORS.text }}>Outputs:</span> predictions and metrics paths defined in YAML; Veritas maps them to reports for the requester.</li>
                <li><span style={{ color: COLORS.text }}>Licenses:</span> FreeSurfer <code className="rounded bg-slate-100 px-1 text-xs">license.txt</code> and MELD <code className="rounded bg-slate-100 px-1 text-xs">meld_license.txt</code> on the host; mounted read-only in the job script.</li>
              </ul>
              <p className="mt-4 text-xs" style={{ color: COLORS.muted }}>
                Use the Pipeline page to preview operator YAML; after approval, Veritas admin connects to your HPC and submits Slurm jobs against the registered pipeline.
              </p>
            </Card>
          </div>
        </PageShell>
      )}

      {page === "pipeline" && (
        <PageShell>
          <SectionTitle
            title="Pipeline"
            subtitle="You submit a container image from the User Dashboard (e.g. MELD Graph for IDEAS). Operators register this YAML in the Veritas catalog (POST /api/v1/pipelines): inputs/outputs, runtime_profile, and for MELD the plugin block with FreeSurfer/MELD license file names and mount paths. Then Veritas admin runs Slurm jobs against that catalog entry."
          />
          <div className="grid gap-5 xl:grid-cols-12">
            <Card className="p-5 sm:p-6 xl:col-span-5">
              <h3 className="text-lg font-semibold sm:text-xl" style={{ color: COLORS.text }}>Pipeline details</h3>
              <p className="mt-2 text-sm leading-relaxed" style={{ color: COLORS.muted }}>
                {pipelineTemplate === "meld_graph"
                  ? "MELD Graph expects a BIDS T1w layout, FreeSurfer + MELD license files on the host (see plugin.secrets), and optional IDEAS/Atlas staging paths. The generated Slurm script wraps docker run / apptainer with those mounts."
                  : pipelineDraft.description}
              </p>
              <div className="mt-4">
                <SelectField
                  label="YAML template"
                  options={[
                    { name: "MELD Graph (IDEAS / FCD)" },
                    { name: "Generic biomarker" },
                  ]}
                  value={pipelineTemplate === "meld_graph" ? "MELD Graph (IDEAS / FCD)" : "Generic biomarker"}
                  onChange={(e) => setPipelineTemplate(e.target.value === "MELD Graph (IDEAS / FCD)" ? "meld_graph" : "generic")}
                />
              </div>
              <div className="mt-5 grid gap-4">
                <TextField label="Pipeline name (YAML name)" placeholder="my-biomarker" value={pipelineDraft.name} onChange={(e) => setPipelineDraft({ ...pipelineDraft, name: e.target.value })} />
                <TextField label="Display title" placeholder="My biomarker pipeline" value={pipelineDraft.title} onChange={(e) => setPipelineDraft({ ...pipelineDraft, title: e.target.value })} />
                <TextField
                  label="Container image (after docker push)"
                  placeholder="docker.io/phindagijimana321/my-biomarker:v1"
                  value={pipelineDraft.image}
                  onChange={(e) => setPipelineDraft({ ...pipelineDraft, image: e.target.value })}
                  className="font-mono text-xs"
                />
                <TextField label="Modality" placeholder="MRI" value={pipelineDraft.modality} onChange={(e) => setPipelineDraft({ ...pipelineDraft, modality: e.target.value })} />
                <TextField
                  label="Entrypoint / command"
                  placeholder="python /app/run.py --input /input --output /output"
                  value={pipelineDraft.entrypoint}
                  onChange={(e) => setPipelineDraft({ ...pipelineDraft, entrypoint: e.target.value })}
                  className="font-mono text-xs"
                />
              </div>
            </Card>
            <Card className="p-5 sm:p-6 xl:col-span-7">
              <h3 className="text-lg font-semibold sm:text-xl" style={{ color: COLORS.text }}>YAML definition (operator preview)</h3>
              <p className="mt-2 text-sm" style={{ color: COLORS.muted }}>
                Register with <code className="rounded bg-slate-100 px-1 text-xs">POST /api/v1/pipelines</code>. Jobs resolve <code className="rounded bg-slate-100 px-1 text-xs">pipeline_name</code> or the container <code className="rounded bg-slate-100 px-1 text-xs">image</code> to this YAML (MELD includes <code className="rounded bg-slate-100 px-1 text-xs">plugin</code> for licenses and sidecars).
              </p>
              <div className="mt-5 rounded-2xl border p-4" style={{ borderColor: COLORS.line, backgroundColor: COLORS.soft }}>
                <pre className="overflow-x-auto whitespace-pre-wrap text-sm leading-6 font-mono" style={{ color: COLORS.text }}>{pipelineYamlPreview}</pre>
              </div>
              {pipelinesLive && pipelinesLive.length > 0 ? (
                <div className="mt-6">
                  <h4 className="text-sm font-semibold uppercase tracking-wide" style={{ color: COLORS.muted }}>
                    Live catalog (GET /pipelines)
                  </h4>
                  <ul className="mt-3 space-y-2 text-sm" style={{ color: COLORS.text }}>
                    {pipelinesLive.slice(0, 12).map((p) => (
                      <li key={p.name || p.id} className="rounded-xl border px-3 py-2" style={{ borderColor: COLORS.line }}>
                        <span className="font-medium" style={{ color: COLORS.navy }}>{p.name}</span>
                        {p.title ? <span className="text-slate-600"> — {p.title}</span> : null}
                        {p.image ? (
                          <div className="mt-1 font-mono text-xs" style={{ color: COLORS.muted }}>
                            {p.image}
                          </div>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </Card>
          </div>
        </PageShell>
      )}

      {page === "leaderboard" && (
        <PageShell>
          <SectionTitle title="Leaderboard" subtitle="Consented pipelines published with their benchmark scores." />
          <div className="space-y-5">
            {Object.entries(LEADERBOARD).map(([group, rows]) => (
              <Card key={group} className="overflow-hidden">
                <div className="flex flex-col gap-2 border-b px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6" style={{ borderColor: COLORS.line }}>
                  <div>
                    <h3 className="text-lg font-semibold sm:text-xl" style={{ color: COLORS.text }}>{group} Leaderboard</h3>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-[720px] w-full text-left text-sm">
                    <thead style={{ backgroundColor: COLORS.navySoft, color: COLORS.text }}>
                      <tr>{["Rank", "Pipeline", "Dataset", "Primary Score", "Metric", "Published"].map((heading) => <th key={heading} className="px-4 py-3 font-medium">{heading}</th>)}</tr>
                    </thead>
                    <tbody>
                      {rows.map((entry, idx) => (
                        <tr key={`${group}-${entry.pipeline}`} className={idx !== rows.length - 1 ? "border-t" : ""} style={{ borderColor: COLORS.line }}>
                          <td className="px-4 py-4" style={{ color: COLORS.text }}>#{entry.rank}</td>
                          <td className="px-4 py-4" style={{ color: COLORS.text }}>{entry.pipeline}</td>
                          <td className="px-4 py-4" style={{ color: COLORS.muted }}>{entry.dataset}</td>
                          <td className="px-4 py-4"><span className="rounded-full border px-3 py-1 text-xs" style={{ borderColor: COLORS.line, backgroundColor: COLORS.soft, color: COLORS.navy }}>{entry.score.toFixed(2)}</span></td>
                          <td className="px-4 py-4" style={{ color: COLORS.muted }}>{entry.metric}</td>
                          <td className="px-4 py-4" style={{ color: COLORS.muted }}>{entry.published}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            ))}
          </div>
        </PageShell>
      )}

      {page === "admin" && (
        <PageShell>
          <SectionTitle
            title="Veritas admin"
            subtitle="Flow: the user submitted a pipeline image from their dashboard; you registered YAML (MELD or generic) in the catalog. Connect to your cluster over SSH, then preview or submit Slurm jobs for the selected evaluation request. Set HPC_MODE=slurm on the API for real sbatch; mock mode still exercises the API without SSH."
          />
          {reportStatus ? (
            <div className="mb-5 rounded-2xl border px-4 py-3 text-sm" style={{ borderColor: "#bbf7d0", backgroundColor: "#ecfdf3", color: "#166534" }}>
              {reportStatus}
            </div>
          ) : null}
          <div className="grid gap-5 xl:grid-cols-12 items-stretch">
            <Card className="p-5 xl:col-span-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold" style={{ color: COLORS.text }}>HPC connection</h3>
                  <p className="mt-1 text-sm" style={{ color: COLORS.muted }}>
                    Uses <code className="rounded bg-white px-1 text-xs">POST /api/v1/hpc/connect</code> (Paramiko SSH). {hpcSummary?.hpc_mode === "slurm" ? "API is in Slurm mode — sbatch runs on this host." : "API is in mock mode — jobs are simulated unless you set HPC_MODE=slurm."}
                  </p>
                </div>
                <span
                  className="shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium"
                  style={{
                    borderColor: activeHpc ? "#bbf7d0" : COLORS.line,
                    backgroundColor: activeHpc ? "#ecfdf3" : COLORS.soft,
                    color: activeHpc ? "#166534" : COLORS.muted,
                  }}
                >
                  {activeHpc ? "SSH OK" : "Not connected"}
                </span>
              </div>
              {hpcSummaryError && isVeritasApiConfigured() ? (
                <p className="mt-2 text-xs text-amber-800">{hpcSummaryError}</p>
              ) : null}
              <div className="mt-4 rounded-2xl border p-4" style={{ borderColor: COLORS.line, backgroundColor: COLORS.navySoft }}>
                <div className="grid grid-cols-3 gap-2">
                  <SmallStat value={hpcSummaryLoading ? "…" : hpcSummary != null ? hpcSummary.queued : "—"} label="Queued" />
                  <SmallStat value={hpcSummaryLoading ? "…" : hpcSummary != null ? hpcSummary.running : "—"} label="Running" />
                  <SmallStat value={hpcSummaryLoading ? "…" : hpcSummary != null ? hpcSummary.gpu_free : "—"} label="GPU free" />
                </div>
              </div>
              {activeHpc && hpcSummary?.active_connection ? (
                <p className="mt-4 text-sm leading-relaxed" style={{ color: COLORS.muted }}>
                  <span className="font-medium" style={{ color: COLORS.text }}>
                    {hpcSummary.active_connection.username}@{hpcSummary.active_connection.hostname}
                  </span>
                  <span> · port {hpcSummary.active_connection.port}</span>
                </p>
              ) : (
                <p className="mt-4 text-sm" style={{ color: COLORS.muted }}>
                  {isVeritasApiConfigured() ? "Open Veritas API URL in VITE_VERITAS_API_BASE_URL, then save SSH below." : "Set VITE_VERITAS_API_BASE_URL (e.g. /api/v1) to load queue stats and connect."}
                </p>
              )}
              <button
                type="button"
                onClick={() => {
                  setShowSlurmModal(false);
                  setShowReportModal(false);
                  setHpcModalMessage(null);
                  setShowHpcModal(true);
                }}
                className="mt-5 w-full rounded-full px-5 py-3 text-sm font-medium text-white"
                style={{ backgroundColor: COLORS.navy }}
              >
                {activeHpc ? "Edit HPC connection" : "Connect to HPC"}
              </button>
            </Card>

            <Card className="overflow-hidden xl:col-span-8">
              <div className="border-b px-5 py-4" style={{ borderColor: COLORS.line, backgroundColor: COLORS.navySoft }}>
                <h3 className="text-lg font-semibold" style={{ color: COLORS.text }}>Submitted requests</h3>
                <p className="mt-1 text-sm" style={{ color: COLORS.muted }}>Choose a request to attach Slurm jobs and reports.</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead style={{ backgroundColor: "#fff", color: COLORS.text }}>
                    <tr>
                      {["Request", "Requester", "Dataset", "Phase", "Report"].map((h) => (
                        <th key={h} className="border-b px-4 py-3 font-medium" style={{ borderColor: COLORS.line }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {requests.map((row, idx) => {
                      const active = selectedRequestId === row.id;
                      return (
                        <tr
                          key={row.id}
                          onClick={() => setSelectedRequestId(row.id)}
                          className={idx < requests.length - 1 ? "border-b" : ""}
                          style={{
                            borderColor: COLORS.line,
                            cursor: "pointer",
                            backgroundColor: active ? "#eff6ff" : undefined,
                          }}
                        >
                          <td className="px-4 py-3 font-mono text-xs" style={{ color: COLORS.navy }}>
                            {row.id}
                          </td>
                          <td className="px-4 py-3" style={{ color: COLORS.text }}>
                            {row.user}
                            <div className="text-xs" style={{ color: COLORS.muted }}>
                              {row.requesterEmail}
                            </div>
                          </td>
                          <td className="px-4 py-3" style={{ color: COLORS.muted }}>
                            {row.datasets}
                          </td>
                          <td className="px-4 py-3" style={{ color: COLORS.text }}>
                            {row.phase}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className="rounded-full border px-2 py-0.5 text-xs font-medium"
                              style={{
                                borderColor: COLORS.line,
                                backgroundColor: row.report === "Ready" ? "#ecfdf3" : COLORS.soft,
                                color: row.report === "Ready" ? "#166534" : COLORS.muted,
                              }}
                            >
                              {row.report}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card className="p-5 sm:p-6 xl:col-span-12">
              <div className="grid gap-8 lg:grid-cols-2">
                <div>
                  <h3 className="text-lg font-semibold" style={{ color: COLORS.text }}>
                    Selected request · {selectedRequest.id}
                  </h3>
                  <p className="mt-2 text-sm" style={{ color: COLORS.muted }}>
                    Pipeline <code className="rounded bg-slate-100 px-1 text-xs">{selectedRequest.pipeline}</code>
                  </p>
                  <TextField
                    label="Internal admin note"
                    textarea
                    className="mt-4 min-h-[100px]"
                    placeholder="Notes visible to operators…"
                    value={adminNote}
                    onChange={(e) => setAdminNote(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() =>
                      setRequests((prev) =>
                        prev.map((r) => (r.id === selectedRequest.id ? { ...r, admin_note: adminNote } : r)),
                      )
                    }
                    className="mt-3 rounded-full border px-4 py-2 text-sm font-medium"
                    style={{ borderColor: COLORS.line, color: COLORS.navy }}
                  >
                    Save note
                  </button>
                </div>
                <div className="flex flex-col justify-center gap-3 rounded-2xl border p-5" style={{ borderColor: COLORS.line, backgroundColor: COLORS.soft }}>
                  <p className="text-sm font-medium" style={{ color: COLORS.text }}>Actions</p>
                  <button
                    type="button"
                    onClick={() => {
                      const isMeld = selectedRequest.pipeline.includes("meld");
                      setSlurmForm((f) => ({
                        ...f,
                        job_name: `eval-${selectedRequest.id.toLowerCase().replace(/\s/g, "")}`,
                        dataset: selectedRequest.atlasId === "ideas" ? "ideas" : "dataset",
                        pipeline_image: selectedRequest.pipeline,
                        pipeline_name: isMeld ? "meld-graph-fcd" : "",
                        runtime_profile: isMeld ? "meld_graph" : "generic",
                        meld_subject_id: isMeld ? "sub-01" : "",
                      }));
                      setShowHpcModal(false);
                      setShowReportModal(false);
                      setJobPreview({ loading: false, error: null, data: null });
                      setSlurmPreviewTab("sbatch");
                      setShowSlurmModal(true);
                      if (isVeritasApiConfigured()) {
                        refreshHpcSummary();
                      }
                    }}
                    className="rounded-full px-5 py-3 text-sm font-medium text-white"
                    style={{ backgroundColor: COLORS.navy }}
                  >
                    Submit job (Slurm resources)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setReportForm({
                        subject: `Veritas validation report — ${selectedRequest.id}`,
                        body: `Dear ${selectedRequest.user},\n\nYour evaluation request ${selectedRequest.id} is ready. Metrics and PDF are attached in the platform.\n\n— Veritas operations`,
                      });
                      setShowHpcModal(false);
                      setShowSlurmModal(false);
                      setShowReportModal(true);
                    }}
                    className="rounded-full border px-5 py-3 text-sm font-medium"
                    style={{ borderColor: COLORS.line, color: COLORS.navy }}
                  >
                    Send report to requester
                  </button>
                  <p className="text-xs leading-relaxed" style={{ color: COLORS.muted }}>
                    <code className="rounded bg-white px-1">POST …/jobs/preview/{"{request_id}"}</code> (dry run) and{" "}
                    <code className="rounded bg-white px-1">POST …/jobs/submit/{"{request_id}"}</code> (Slurm when HPC_MODE=slurm). Notify the requester when the report is ready.
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </PageShell>
      )}

      {showHpcModal ? (
        <ModalShell
          title="HPC connection (SSH)"
          subtitle="Calls the Veritas API: Test runs SSH only; Save validates SSH and stores this as the active cluster connection for Slurm submit when HPC_MODE=slurm. Leave key path empty to use ssh-agent / default keys on the API host."
          onClose={() => {
            setShowHpcModal(false);
            setHpcModalMessage(null);
          }}
          footer={
            <>
              <button
                type="button"
                onClick={() => {
                  setShowHpcModal(false);
                  setHpcModalMessage(null);
                }}
                className="rounded-full border px-5 py-3 text-sm font-medium"
                style={{ borderColor: COLORS.line, color: COLORS.navy }}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={hpcModalBusy || !isVeritasApiConfigured()}
                onClick={async () => {
                  if (!isVeritasApiConfigured()) {
                    setHpcModalMessage({ error: "Set VITE_VERITAS_API_BASE_URL (e.g. /api/v1)." });
                    return;
                  }
                  setHpcModalBusy(true);
                  setHpcModalMessage(null);
                  const res = await testHpcConnection(buildHpcConnectPayload(hpcForm));
                  setHpcModalBusy(false);
                  if (res.ok) {
                    setHpcModalMessage({ ok: "SSH test succeeded (not saved)." });
                  } else {
                    setHpcModalMessage({ error: res.message });
                  }
                }}
                className="rounded-full border px-5 py-3 text-sm font-medium disabled:opacity-50"
                style={{ borderColor: COLORS.line, color: COLORS.navy }}
              >
                {hpcModalBusy ? "Testing…" : "Test SSH"}
              </button>
              <button
                type="button"
                disabled={hpcModalBusy || !isVeritasApiConfigured()}
                onClick={async () => {
                  if (!isVeritasApiConfigured()) {
                    setHpcModalMessage({ error: "Set VITE_VERITAS_API_BASE_URL (e.g. /api/v1)." });
                    return;
                  }
                  setHpcModalBusy(true);
                  setHpcModalMessage(null);
                  const res = await connectHpc(buildHpcConnectPayload(hpcForm));
                  setHpcModalBusy(false);
                  if (res.ok) {
                    await refreshHpcSummary();
                    setShowHpcModal(false);
                    setHpcModalMessage(null);
                    setReportStatus(`HPC connected: ${res.data.username}@${res.data.hostname}`);
                  } else {
                    setHpcModalMessage({ error: res.message });
                  }
                }}
                className="rounded-full px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
                style={{ backgroundColor: COLORS.navy }}
              >
                {hpcModalBusy ? "Connecting…" : "Save & connect"}
              </button>
            </>
          }
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Hostname" placeholder="e.g. login.hpc.cluster.org" value={hpcForm.hostname} onChange={(e) => setHpcForm({ ...hpcForm, hostname: e.target.value })} />
            <TextField label="Username" placeholder="researcher" value={hpcForm.username} onChange={(e) => setHpcForm({ ...hpcForm, username: e.target.value })} />
            <TextField label="Port" placeholder="22" value={hpcForm.port} onChange={(e) => setHpcForm({ ...hpcForm, port: e.target.value })} />
            <TextField label="SSH private key path (optional)" placeholder="~/.ssh/id_ed25519" value={hpcForm.key_path} onChange={(e) => setHpcForm({ ...hpcForm, key_path: e.target.value })} />
            <div className="sm:col-span-2">
              <TextField label="Notes" placeholder="Partition hints, VPN, Apptainer module…" value={hpcForm.notes} onChange={(e) => setHpcForm({ ...hpcForm, notes: e.target.value })} />
            </div>
          </div>
          {hpcModalMessage?.error ? (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-900" role="alert">
              {hpcModalMessage.error}
            </div>
          ) : null}
          {hpcModalMessage?.ok ? (
            <div className="mt-4 rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-900">
              {hpcModalMessage.ok}
            </div>
          ) : null}
        </ModalShell>
      ) : null}

      {showSlurmModal ? (
        <ModalShell
          title="Submit Slurm job"
          subtitle={`Request ${selectedRequest.id} · ${selectedRequest.user} · preview POST /api/v1/jobs/preview/${selectedRequest.id} · submit POST /api/v1/jobs/submit/${selectedRequest.id}`}
          panelClassName="max-w-5xl"
          onClose={() => {
            setShowSlurmModal(false);
            setJobPreview({ loading: false, error: null, data: null });
          }}
          footer={
            <>
              <button
                type="button"
                onClick={() => {
                  setShowSlurmModal(false);
                  setJobPreview({ loading: false, error: null, data: null });
                }}
                className="rounded-full border px-5 py-3 text-sm font-medium"
                style={{ borderColor: COLORS.line, color: COLORS.navy }}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={jobPreview.loading || submitJobLoading}
                onClick={async () => {
                  if (!isVeritasApiConfigured()) {
                    setJobPreview({
                      loading: false,
                      error: "Set VITE_VERITAS_API_BASE_URL (e.g. /api/v1 with the Vite proxy to your Veritas API).",
                      data: null,
                    });
                    return;
                  }
                  if (!slurmForm.job_name.trim() || !slurmForm.pipeline_image.trim() || !slurmForm.dataset.trim()) {
                    setJobPreview({ loading: false, error: "Job name, pipeline image, and dataset are required.", data: null });
                    return;
                  }
                  if (slurmForm.runtime_profile === "meld_graph" && !slurmForm.meld_subject_id.trim()) {
                    setJobPreview({
                      loading: false,
                      error: "MELD subject id is required when runtime profile is meld_graph.",
                      data: null,
                    });
                    return;
                  }
                  setJobPreview({ loading: true, error: null, data: null });
                  setSlurmPreviewTab("sbatch");
                  const res = await previewSlurmJob(selectedRequest.id, buildSlurmSubmitPayload(slurmForm));
                  if (res.ok) {
                    setJobPreview({ loading: false, error: null, data: res.data });
                  } else {
                    setJobPreview({ loading: false, error: res.message, data: null });
                  }
                }}
                className="rounded-full border px-5 py-3 text-sm font-medium disabled:opacity-50"
                style={{ borderColor: COLORS.line, color: COLORS.navy }}
              >
                {jobPreview.loading ? "Previewing…" : "Preview scripts"}
              </button>
              <button
                type="button"
                disabled={submitJobLoading || slurmSubmitBlocked || !isVeritasApiConfigured()}
                onClick={async () => {
                  if (!isVeritasApiConfigured()) {
                    setJobPreview({
                      loading: false,
                      error: "Set VITE_VERITAS_API_BASE_URL (e.g. /api/v1 with the Vite proxy).",
                      data: null,
                    });
                    return;
                  }
                  if (!slurmForm.job_name.trim() || !slurmForm.pipeline_image.trim() || !slurmForm.dataset.trim()) {
                    setJobPreview({ loading: false, error: "Job name, pipeline image, and dataset are required.", data: null });
                    return;
                  }
                  if (slurmForm.runtime_profile === "meld_graph" && !slurmForm.meld_subject_id.trim()) {
                    setJobPreview({
                      loading: false,
                      error: "MELD subject id is required when runtime profile is meld_graph.",
                      data: null,
                    });
                    return;
                  }
                  if (slurmSubmitBlocked) {
                    setJobPreview({
                      loading: false,
                      error: "Connect to HPC first (API is in HPC_MODE=slurm).",
                      data: null,
                    });
                    return;
                  }
                  setSubmitJobLoading(true);
                  setJobPreview({ loading: false, error: null, data: null });
                  const res = await submitSlurmJob(selectedRequest.id, buildSlurmSubmitPayload(slurmForm));
                  setSubmitJobLoading(false);
                  if (res.ok) {
                    setShowSlurmModal(false);
                    setJobPreview({ loading: false, error: null, data: null });
                    setReportStatus(
                      `Job submitted for ${selectedRequest.id}: ${res.data.id} · scheduler ${res.data.scheduler_job_id || "—"} · status ${res.data.status}`,
                    );
                    await refreshHpcSummary();
                  } else {
                    setJobPreview({ loading: false, error: res.message, data: null });
                  }
                }}
                className="rounded-full px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
                style={{ backgroundColor: COLORS.navy }}
              >
                {submitJobLoading ? "Submitting…" : "Submit job"}
              </button>
            </>
          }
        >
          {slurmSubmitBlocked ? (
            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
              The API is in <strong>HPC_MODE=slurm</strong>: connect to your cluster (SSH) from the HPC card before submitting. In <strong>mock</strong> mode, submit works without SSH.
            </div>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Job name" value={slurmForm.job_name} onChange={(e) => setSlurmForm({ ...slurmForm, job_name: e.target.value })} />
            <TextField label="Partition" placeholder="gpu" value={slurmForm.partition} onChange={(e) => setSlurmForm({ ...slurmForm, partition: e.target.value })} />
            <div className="sm:col-span-2">
              <SelectField
                label="Resource preset"
                options={SLURM_PRESETS}
                value={slurmForm.resources}
                onChange={(e) => setSlurmForm({ ...slurmForm, resources: e.target.value })}
              />
            </div>
            <TextField label="GPUs" value={slurmForm.gpus} onChange={(e) => setSlurmForm({ ...slurmForm, gpus: e.target.value })} />
            <TextField label="CPUs" value={slurmForm.cpus} onChange={(e) => setSlurmForm({ ...slurmForm, cpus: e.target.value })} />
            <TextField label="Memory (GB)" value={slurmForm.memory_gb} onChange={(e) => setSlurmForm({ ...slurmForm, memory_gb: e.target.value })} />
            <TextField label="Wall time" placeholder="24:00:00" value={slurmForm.wall_time} onChange={(e) => setSlurmForm({ ...slurmForm, wall_time: e.target.value })} />
            <TextField label="Constraint (optional)" placeholder="a100" value={slurmForm.constraint} onChange={(e) => setSlurmForm({ ...slurmForm, constraint: e.target.value })} />
            <TextField label="Dataset (job)" value={slurmForm.dataset} onChange={(e) => setSlurmForm({ ...slurmForm, dataset: e.target.value })} />
            <TextField label="Pipeline image" value={slurmForm.pipeline_image} onChange={(e) => setSlurmForm({ ...slurmForm, pipeline_image: e.target.value })} />
            <TextField label="Pipeline name (optional)" placeholder="meld-graph-fcd" value={slurmForm.pipeline_name} onChange={(e) => setSlurmForm({ ...slurmForm, pipeline_name: e.target.value })} />
            <SelectField
              label="Runtime profile"
              options={["generic", "meld_graph"]}
              value={slurmForm.runtime_profile}
              onChange={(e) => setSlurmForm({ ...slurmForm, runtime_profile: e.target.value })}
            />
            {slurmForm.runtime_profile === "meld_graph" ? (
              <TextField label="MELD subject id" placeholder="sub-01" value={slurmForm.meld_subject_id} onChange={(e) => setSlurmForm({ ...slurmForm, meld_subject_id: e.target.value })} />
            ) : null}
            <div className="sm:col-span-2">
              <TextField
                label="#SBATCH overrides (optional)"
                textarea
                className="min-h-[88px] font-mono text-xs"
                placeholder="#SBATCH --gres=gpu:1"
                value={slurmForm.sbatch_overrides}
                onChange={(e) => setSlurmForm({ ...slurmForm, sbatch_overrides: e.target.value })}
              />
            </div>
          </div>
          {jobPreview.error ? (
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-900" role="alert">
              {jobPreview.error}
            </div>
          ) : null}
          {jobPreview.data ? (
            <div className="mt-6 rounded-2xl border p-4" style={{ borderColor: COLORS.line, backgroundColor: COLORS.soft }}>
              <p className="text-sm font-medium" style={{ color: COLORS.text }}>
                Preview (no job submitted)
              </p>
              <dl className="mt-2 grid gap-1 text-xs sm:grid-cols-2" style={{ color: COLORS.muted }}>
                <div>
                  <dt className="inline font-medium" style={{ color: COLORS.text }}>runtime_engine: </dt>
                  <dd className="inline font-mono">{jobPreview.data.runtime_engine}</dd>
                </div>
                <div>
                  <dt className="inline font-medium" style={{ color: COLORS.text }}>hpc_mode: </dt>
                  <dd className="inline font-mono">{jobPreview.data.hpc_mode}</dd>
                </div>
                {jobPreview.data.meld_ideas_default_staging_path ? (
                  <div className="sm:col-span-2">
                    <dt className="inline font-medium" style={{ color: COLORS.text }}>meld_ideas_default_staging_path: </dt>
                    <dd className="inline break-all font-mono">{jobPreview.data.meld_ideas_default_staging_path}</dd>
                  </div>
                ) : null}
              </dl>
              <div className="mt-3 flex flex-wrap gap-2">
                {[
                  { id: "sbatch", label: "Slurm sbatch" },
                  { id: "pipeline", label: "Pipeline runtime" },
                  { id: "paths", label: "Paths & launch" },
                ].map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setSlurmPreviewTab(t.id)}
                    className="rounded-full border px-3 py-1.5 text-xs font-medium"
                    style={{
                      borderColor: slurmPreviewTab === t.id ? "#bfdbfe" : COLORS.line,
                      backgroundColor: slurmPreviewTab === t.id ? "#eff6ff" : "#ffffff",
                      color: COLORS.navy,
                    }}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              {slurmPreviewTab === "paths" ? (
                <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-xl border bg-white p-3 text-xs" style={{ borderColor: COLORS.line, color: COLORS.text }}>
                  {[
                    `remote_workdir: ${jobPreview.data.remote_workdir}`,
                    `stdout: ${jobPreview.data.stdout_path}`,
                    `stderr: ${jobPreview.data.stderr_path}`,
                    `runtime_manifest: ${jobPreview.data.runtime_manifest_path}`,
                    `metrics: ${jobPreview.data.metrics_path}`,
                    `results_csv: ${jobPreview.data.results_csv_path}`,
                    `report: ${jobPreview.data.report_path}`,
                    "",
                    `launch_command:`,
                    jobPreview.data.launch_command,
                  ].join("\n")}
                </pre>
              ) : (
                <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded-xl border bg-white p-3 text-xs" style={{ borderColor: COLORS.line, color: COLORS.text }}>
                  {slurmPreviewTab === "sbatch"
                    ? jobPreview.data.sbatch_script
                    : jobPreview.data.pipeline_runtime_script || "— (no pipeline runtime script for this profile)"}
                </pre>
              )}
            </div>
          ) : null}
        </ModalShell>
      ) : null}

      {showReportModal ? (
        <ModalShell
          title="Send report to requester"
          subtitle={`To: ${selectedRequest.requesterEmail} · ${selectedRequest.user}`}
          onClose={() => setShowReportModal(false)}
          footer={
            <>
              <button type="button" onClick={() => setShowReportModal(false)} className="rounded-full border px-5 py-3 text-sm font-medium" style={{ borderColor: COLORS.line, color: COLORS.navy }}>
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  setRequests((prev) =>
                    prev.map((r) =>
                      r.id === selectedRequest.id ? { ...r, report: "Ready", admin_note: adminNote } : r,
                    ),
                  );
                  setReportStatus(`Report sent to ${selectedRequest.requesterEmail} for ${selectedRequest.id} (demo).`);
                  setShowReportModal(false);
                }}
                className="rounded-full px-5 py-3 text-sm font-medium text-white"
                style={{ backgroundColor: COLORS.navy }}
              >
                Send report
              </button>
            </>
          }
        >
          <div className="grid gap-4">
            <TextField label="Subject" value={reportForm.subject} onChange={(e) => setReportForm({ ...reportForm, subject: e.target.value })} />
            <TextField label="Message" textarea className="min-h-[160px]" value={reportForm.body} onChange={(e) => setReportForm({ ...reportForm, body: e.target.value })} />
            <p className="text-xs" style={{ color: COLORS.muted }}>
              Production: attach PDF/JSON/CSV artifact URLs from Veritas report storage.
            </p>
          </div>
        </ModalShell>
      ) : null}
    </div>
  );
}
