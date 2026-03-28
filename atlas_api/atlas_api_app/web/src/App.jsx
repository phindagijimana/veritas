import React, { useMemo, useState } from "react";
import {
  Database,
  ServerCog,
  Github,
  Brain,
  X,
  Mail,
  Building2,
  FileText,
  ShieldCheck,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const COLORS = {
  navy: "#0f2f6b",
  navySoft: "#eaf1fb",
  line: "#d7e2f2",
  text: "#16325c",
  muted: "#5e7394",
  bg: "#f6f9fe",
  soft: "#f8fbff",
  success: "#166534",
  successBg: "#ecfdf3",
  warning: "#92400e",
  warningBg: "#fff7ed",
  danger: "#b91c1c",
  dangerBg: "#fef2f2",
};

const BASE_ACCESS_REQUESTS = [
  {
    id: "REQ-1001",
    dataset: "OpenNeuro Epilepsy MRI",
    email: "jane.smith@university.edu",
    institution: "University Research Lab",
    purpose: "Download public neuroimaging datasets for ML training.",
    status: "pending",
    submittedAt: "2026-03-09 09:15",
  },
  {
    id: "REQ-1002",
    dataset: "HS Validation Dataset",
    email: "alex.chen@hospital.org",
    institution: "Clinical AI Group",
    purpose: "Request API access for dataset discovery and validation workflows.",
    status: "approved",
    submittedAt: "2026-03-08 14:20",
  },
  {
    id: "REQ-1003",
    dataset: "Brain Tumor Segmentation",
    email: "data.team@startup.ai",
    institution: "Startup AI",
    purpose: "Evaluate public datasets for benchmarking experiments.",
    status: "denied",
    submittedAt: "2026-03-07 11:05",
  },
];

const INITIAL_ACCESS_REQUESTS = Array.from({ length: 18 }).map((_, i) => {
  const base = BASE_ACCESS_REQUESTS[i % BASE_ACCESS_REQUESTS.length];
  return {
    ...base,
    id: `${base.id}-${i + 1}`,
  };
});

const BASE_STAGING_REQUESTS = [
  {
    id: "STG-3001",
    dataset: "HS Validation Dataset",
    compute: "URMC HPC",
    requestedBy: "veritas_service",
    requestedAt: "2026-03-09 10:00",
    status: "pending",
  },
  {
    id: "STG-3002",
    dataset: "Brain Tumor Segmentation",
    compute: "URMC HPC",
    requestedBy: "neuroinsight_platform",
    requestedAt: "2026-03-08 15:40",
    status: "approved",
  },
];

const INITIAL_STAGING_REQUESTS = Array.from({ length: 14 }).map((_, i) => {
  const base = BASE_STAGING_REQUESTS[i % BASE_STAGING_REQUESTS.length];
  return {
    ...base,
    id: `${base.id}-${i + 1}`,
  };
});

const BASE_ACCESS_GRANTS = [
  {
    id: "ACC-2001",
    email: "alex.chen@hospital.org",
    scope: "Public + restricted metadata",
    sentAt: "2026-03-08 16:00",
    status: "active",
  },
  {
    id: "ACC-2002",
    email: "admin@veritas.local",
    scope: "Admin",
    sentAt: "2026-03-06 10:30",
    status: "active",
  },
];

const INITIAL_ACCESS_GRANTS = Array.from({ length: 12 }).map((_, i) => {
  const base = BASE_ACCESS_GRANTS[i % BASE_ACCESS_GRANTS.length];
  const [local, domain] = base.email.split("@");
  return {
    ...base,
    id: `${base.id}-${i + 1}`,
    email: `${local}+${i}@${domain}`,
  };
});

const features = [
  {
    icon: Database,
    title: "Dataset registry",
    text: "Versioned biomedical datasets with validation and controlled access.",
  },
  {
    icon: ServerCog,
    title: "Validation-ready",
    text: "Ready for controlled staging and evaluation workflows in platforms like Veritas.",
  },
  {
    icon: Brain,
    title: "Training-ready",
    text: "Public Pennsieve datasets can be used for training; validation datasets remain controlled.",
  },
  {
    icon: ShieldCheck,
    title: "Access control",
    text: "Administrators manage API credentials, Pennsieve access policies, staging approvals, and usage oversight.",
  },
];

function statusPill(status) {
  const normalized = status.toLowerCase();
  if (normalized === "approved" || normalized === "active") {
    return {
      color: COLORS.success,
      backgroundColor: COLORS.successBg,
      borderColor: "#bbf7d0",
    };
  }
  if (normalized === "pending") {
    return {
      color: COLORS.warning,
      backgroundColor: COLORS.warningBg,
      borderColor: "#fed7aa",
    };
  }
  return {
    color: COLORS.danger,
    backgroundColor: COLORS.dangerBg,
    borderColor: "#fecaca",
  };
}

function Field({ label, icon: Icon, children }) {
  return (
    <div>
      <label className="mb-2 block text-sm" style={{ color: COLORS.muted }}>
        {label}
      </label>
      <div className="flex items-start gap-3 rounded-2xl border px-4 py-3" style={{ borderColor: COLORS.line }}>
        <Icon className="mt-0.5 h-4 w-4 shrink-0" style={{ color: COLORS.muted }} />
        <div className="w-full">{children}</div>
      </div>
    </div>
  );
}

function AccessRequestModal({ open, onClose }) {
  const [form, setForm] = useState({
    email: "",
    institution: "",
    accessType: "public",
    purpose: "",
    environment: "URMC HPC",
    validationJustification: "",
    platformName: "",
    projectName: "",
    principalInvestigator: "",
    hpcUsername: "",
    remotePlatform: "",
    acknowledgeControlledUse: false,
  });
  const [submitted, setSubmitted] = useState(false);

  if (!open) return null;

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
  };

  const isValidation = form.accessType === "validation";
  const isUrmcHpc = form.environment === "URMC HPC";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
      <div className="w-full max-w-2xl rounded-3xl border bg-white shadow-2xl" style={{ borderColor: COLORS.line }}>
        <div className="flex items-center justify-between border-b px-6 py-5" style={{ borderColor: COLORS.line }}>
          <div>
            <h2 className="text-2xl font-semibold" style={{ color: COLORS.text }}>
              Request API Access
            </h2>
            <p className="mt-1 text-sm" style={{ color: COLORS.muted }}>
              Submit your details to request Atlas API credentials for public or validation dataset access.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full border p-2"
            style={{ borderColor: COLORS.line, color: COLORS.text }}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-[75vh] overflow-y-auto p-6">
          {submitted ? (
            <div className="rounded-2xl border px-5 py-4" style={{ borderColor: COLORS.line, backgroundColor: COLORS.navySoft }}>
              <h3 className="text-lg font-semibold" style={{ color: COLORS.text }}>
                Request submitted
              </h3>
              <p className="mt-2 text-sm leading-6" style={{ color: COLORS.muted }}>
                Your API access request has been submitted. If approved, credentials will be sent to your email.
              </p>
              <div className="mt-4">
                <Button onClick={onClose} className="rounded-full" style={{ backgroundColor: COLORS.navy, color: "white" }}>
                  Close
                </Button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <Field label="Email" icon={Mail}>
                <input type="email" required value={form.email} onChange={(e) => updateField("email", e.target.value)} placeholder="name@institution.edu" className="w-full bg-transparent text-sm outline-none" style={{ color: COLORS.text }} />
              </Field>
              <Field label="Institution" icon={Building2}>
                <input type="text" required value={form.institution} onChange={(e) => updateField("institution", e.target.value)} placeholder="University, hospital, company, or lab" className="w-full bg-transparent text-sm outline-none" style={{ color: COLORS.text }} />
              </Field>
              <Field label="Access Type" icon={ShieldCheck}>
                <select value={form.accessType} onChange={(e) => updateField("accessType", e.target.value)} className="w-full bg-transparent text-sm outline-none" style={{ color: COLORS.text }}>
                  <option value="public">Public Pennsieve datasets</option>
                  <option value="validation">Validation datasets (controlled)</option>
                </select>
              </Field>
              <Field label="Purpose of dataset use" icon={FileText}>
                <textarea required value={form.purpose} onChange={(e) => updateField("purpose", e.target.value)} placeholder="Briefly describe how you plan to use Pennsieve-backed Atlas datasets." className="min-h-[120px] w-full resize-none bg-transparent text-sm outline-none" style={{ color: COLORS.text }} />
              </Field>
              <Field label="Project or study name" icon={FileText}>
                <input type="text" required value={form.projectName} onChange={(e) => updateField("projectName", e.target.value)} placeholder="e.g. Epilepsy biomarker validation study" className="w-full bg-transparent text-sm outline-none" style={{ color: COLORS.text }} />
              </Field>
              {isValidation ? (
                <>
                  <Field label="Validation environment" icon={ServerCog}>
                    <select value={form.environment} onChange={(e) => updateField("environment", e.target.value)} className="w-full bg-transparent text-sm outline-none" style={{ color: COLORS.text }}>
                      <option>URMC HPC</option>
                      <option>Remote Server</option>
                      <option>Other approved compute</option>
                    </select>
                  </Field>
                  <Field label="Platform or service requesting access" icon={ShieldCheck}>
                    <input type="text" required value={form.platformName} onChange={(e) => updateField("platformName", e.target.value)} placeholder="e.g. Veritas, NeuroInsight, internal lab workflow" className="w-full bg-transparent text-sm outline-none" style={{ color: COLORS.text }} />
                  </Field>
                  <Field label="Principal investigator or project owner" icon={Building2}>
                    <input type="text" required value={form.principalInvestigator} onChange={(e) => updateField("principalInvestigator", e.target.value)} placeholder="Name of PI, lead researcher, or responsible owner" className="w-full bg-transparent text-sm outline-none" style={{ color: COLORS.text }} />
                  </Field>
                  {isUrmcHpc ? (
                    <Field label="URMC HPC username" icon={ServerCog}>
                      <input type="text" required value={form.hpcUsername} onChange={(e) => updateField("hpcUsername", e.target.value)} placeholder="URMC HPC account or service identity" className="w-full bg-transparent text-sm outline-none" style={{ color: COLORS.text }} />
                    </Field>
                  ) : (
                    <Field label="Remote compute environment" icon={ServerCog}>
                      <input type="text" required value={form.remotePlatform} onChange={(e) => updateField("remotePlatform", e.target.value)} placeholder="Describe the remote server or approved compute environment" className="w-full bg-transparent text-sm outline-none" style={{ color: COLORS.text }} />
                    </Field>
                  )}
                  <Field label="Validation justification" icon={FileText}>
                    <textarea required value={form.validationJustification} onChange={(e) => updateField("validationJustification", e.target.value)} placeholder="Describe why controlled validation dataset access is needed, what workflow will run, and how results will be used." className="min-h-[120px] w-full resize-none bg-transparent text-sm outline-none" style={{ color: COLORS.text }} />
                  </Field>
                  <div className="rounded-2xl border px-4 py-3" style={{ borderColor: COLORS.line, backgroundColor: COLORS.soft }}>
                    <label className="flex items-start gap-3 text-sm" style={{ color: COLORS.text }}>
                      <input type="checkbox" checked={form.acknowledgeControlledUse} onChange={(e) => updateField("acknowledgeControlledUse", e.target.checked)} className="mt-1" required />
                      <span>I understand validation datasets are controlled resources and may only be staged to approved compute environments through approved workflows.</span>
                    </label>
                  </div>
                </>
              ) : null}
              <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:justify-end">
                <Button type="button" variant="outline" onClick={onClose} className="rounded-full" style={{ borderColor: COLORS.line, color: COLORS.navy, backgroundColor: "white" }}>Cancel</Button>
                <Button type="submit" className="rounded-full" style={{ backgroundColor: COLORS.navy, color: "white" }}>Submit Request</Button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function AccessControlPage() {
  const [requests, setRequests] = useState(INITIAL_ACCESS_REQUESTS);
  const [stagingRequests, setStagingRequests] = useState(INITIAL_STAGING_REQUESTS);
  const [grants, setGrants] = useState(INITIAL_ACCESS_GRANTS);
  const [notice, setNotice] = useState("");

  const stats = useMemo(() => {
    const pendingAccess = requests.filter((item) => item.status === "pending").length;
    const pendingStaging = stagingRequests.filter((item) => item.status === "pending").length;
    const approvedRequests = requests.filter((item) => item.status === "approved").length;
    const active = grants.filter((item) => item.status === "active").length;
    return { pendingAccess, pendingStaging, approvedRequests, active };
  }, [requests, stagingRequests, grants]);

  const updateAccessRequest = (id, status) => {
    setRequests((prev) => prev.map((item) => (item.id === id ? { ...item, status } : item)));
    const target = requests.find((item) => item.id === id);
    if (!target) return;
    if (status === "approved") {
      setGrants((prev) => {
        const exists = prev.some((grant) => grant.email === target.email);
        if (exists) return prev;
        return [{ id: `ACC-${Date.now()}`, email: target.email, scope: "Public dataset access", sentAt: new Date().toISOString().slice(0, 16).replace("T", " "), status: "active" }, ...prev];
      });
      setNotice(`API access approved for ${target.email}.`);
    } else {
      setNotice(`API access denied for ${target.email}.`);
    }
  };

  const updateStagingRequest = (id, status) => {
    setStagingRequests((prev) => prev.map((item) => (item.id === id ? { ...item, status } : item)));
    const target = stagingRequests.find((item) => item.id === id);
    if (!target) return;
    setNotice(status === "approved" ? `Staging approved for ${target.dataset} on ${target.compute}.` : `Staging denied for ${target.dataset}.`);
  };

  const sendAccess = (email) => setNotice(`Access credentials sent to ${email}.`);
  const revokeAccess = (id) => {
    setGrants((prev) => prev.map((item) => (item.id === id ? { ...item, status: "revoked" } : item)));
    const grant = grants.find((item) => item.id === id);
    setNotice(grant ? `Access revoked for ${grant.email}.` : "Access revoked.");
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold" style={{ color: COLORS.text }}>Access Control</h1>
          <p className="mt-3 max-w-3xl text-base leading-7" style={{ color: COLORS.muted }}>Review API access requests, manage controlled staging approvals, and monitor active Atlas API credentials.</p>
        </div>
        <div className="rounded-2xl border px-4 py-3 text-sm" style={{ borderColor: COLORS.line, backgroundColor: "white", color: COLORS.text }}>Internal admin dashboard preview</div>
      </div>
      {notice ? <div className="mb-6 rounded-2xl border px-4 py-3 text-sm" style={{ borderColor: COLORS.line, backgroundColor: COLORS.navySoft, color: COLORS.text }}>{notice}</div> : null}
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {[{ label: "Pending API requests", value: stats.pendingAccess }, { label: "Pending staging requests", value: stats.pendingStaging }, { label: "Approved API requests", value: stats.approvedRequests }, { label: "Active credentials", value: stats.active }].map((item) => (
          <Card key={item.label} className="rounded-3xl border shadow-sm" style={{ borderColor: COLORS.line, backgroundColor: "white" }}><CardContent className="p-5"><div className="text-sm" style={{ color: COLORS.muted }}>{item.label}</div><div className="mt-2 text-3xl font-semibold" style={{ color: COLORS.text }}>{item.value}</div></CardContent></Card>
        ))}
      </div>
      <div className="mt-8 space-y-6">
        <Card className="rounded-3xl border shadow-sm" style={{ borderColor: COLORS.line, backgroundColor: "white" }}><CardContent className="p-0"><div className="border-b px-6 py-5" style={{ borderColor: COLORS.line }}><h2 className="text-xl font-semibold" style={{ color: COLORS.text }}>API Access Requests</h2><p className="mt-1 text-sm" style={{ color: COLORS.muted }}>Approve, deny, and send credentials for incoming Atlas API access requests, including public Pennsieve dataset access.</p></div><div className="max-h-[520px] overflow-y-auto scrollbar-thin"><table className="min-w-[760px] w-full text-left text-sm"><thead style={{ backgroundColor: COLORS.navySoft, color: COLORS.text }}><tr>{["Request", "Dataset", "Email", "Institution", "Status", "API Access"].map((heading) => <th key={heading} className="px-4 py-3 font-medium">{heading}</th>)}</tr></thead><tbody>{requests.map((item, index) => <tr key={item.id} className={index !== requests.length - 1 ? "border-t" : ""} style={{ borderColor: COLORS.line }}><td className="px-4 py-4 align-top"><div className="font-medium" style={{ color: COLORS.text }}>{item.id}</div><div className="mt-1 text-xs" style={{ color: COLORS.muted }}>{item.submittedAt}</div></td><td className="px-4 py-4 align-top" style={{ color: COLORS.text }}>{item.dataset}</td><td className="px-4 py-4 align-top" style={{ color: COLORS.text }}>{item.email}</td><td className="px-4 py-4 align-top"><div style={{ color: COLORS.text }}>{item.institution}</div><div className="mt-1 max-w-xs text-xs leading-5" style={{ color: COLORS.muted }}>{item.purpose}</div></td><td className="px-4 py-4 align-top"><span className="rounded-full border px-3 py-1 text-xs font-medium" style={statusPill(item.status)}>{item.status}</span></td><td className="px-4 py-4 align-top"><div className="flex flex-wrap gap-2"><Button size="sm" className="rounded-full" style={{ backgroundColor: COLORS.navy, color: "white" }} onClick={() => updateAccessRequest(item.id, "approved")}>Approve</Button><Button size="sm" variant="outline" className="rounded-full" style={{ borderColor: COLORS.line, color: COLORS.navy, backgroundColor: "white" }} onClick={() => updateAccessRequest(item.id, "denied")}>Deny</Button><Button size="sm" variant="outline" className="rounded-full" style={{ borderColor: COLORS.line, color: COLORS.text, backgroundColor: "white" }} onClick={() => sendAccess(item.email)}>Send Access</Button></div></td></tr>)}</tbody></table></div></CardContent></Card>
        <Card className="rounded-3xl border shadow-sm" style={{ borderColor: COLORS.line, backgroundColor: "white" }}><CardContent className="p-0"><div className="border-b px-6 py-5" style={{ borderColor: COLORS.line }}><h2 className="text-xl font-semibold" style={{ color: COLORS.text }}>Dataset Staging Requests</h2><p className="mt-1 text-sm" style={{ color: COLORS.muted }}>Approve or deny staging of restricted Pennsieve-backed validation datasets to approved compute environments.</p></div><div className="max-h-[520px] overflow-y-auto scrollbar-thin"><table className="min-w-[760px] w-full text-left text-sm"><thead style={{ backgroundColor: COLORS.navySoft, color: COLORS.text }}><tr>{["Request", "Dataset", "Compute", "Requested By", "Status", "Staging"].map((heading) => <th key={heading} className="px-4 py-3 font-medium">{heading}</th>)}</tr></thead><tbody>{stagingRequests.map((item, index) => <tr key={item.id} className={index !== stagingRequests.length - 1 ? "border-t" : ""} style={{ borderColor: COLORS.line }}><td className="px-4 py-4 align-top"><div className="font-medium" style={{ color: COLORS.text }}>{item.id}</div><div className="mt-1 text-xs" style={{ color: COLORS.muted }}>{item.requestedAt}</div></td><td className="px-4 py-4 align-top" style={{ color: COLORS.text }}>{item.dataset}</td><td className="px-4 py-4 align-top" style={{ color: COLORS.text }}>{item.compute}</td><td className="px-4 py-4 align-top" style={{ color: COLORS.text }}>{item.requestedBy}</td><td className="px-4 py-4 align-top"><span className="rounded-full border px-3 py-1 text-xs font-medium" style={statusPill(item.status)}>{item.status}</span></td><td className="px-4 py-4 align-top"><div className="flex flex-wrap gap-2"><Button size="sm" className="rounded-full" style={{ backgroundColor: COLORS.navy, color: "white" }} onClick={() => updateStagingRequest(item.id, "approved")}>Approve</Button><Button size="sm" variant="outline" className="rounded-full" style={{ borderColor: COLORS.line, color: COLORS.navy, backgroundColor: "white" }} onClick={() => updateStagingRequest(item.id, "denied")}>Deny</Button></div></td></tr>)}</tbody></table></div></CardContent></Card>
        <Card className="rounded-3xl border shadow-sm" style={{ borderColor: COLORS.line, backgroundColor: "white" }}><CardContent className="p-0"><div className="border-b px-6 py-5" style={{ borderColor: COLORS.line }}><h2 className="text-xl font-semibold" style={{ color: COLORS.text }}>Active Credentials</h2><p className="mt-1 text-sm" style={{ color: COLORS.muted }}>Track who currently has Atlas API credentials and manage revocation.</p></div><div className="max-h-[520px] divide-y overflow-y-auto scrollbar-thin" style={{ borderColor: COLORS.line }}>{grants.map((grant) => <div key={grant.id} className="px-6 py-5"><div className="flex items-start justify-between gap-4"><div><div className="font-medium" style={{ color: COLORS.text }}>{grant.email}</div><div className="mt-1 text-sm" style={{ color: COLORS.muted }}>{grant.scope}</div><div className="mt-1 text-xs" style={{ color: COLORS.muted }}>Sent: {grant.sentAt}</div></div><span className="rounded-full border px-3 py-1 text-xs font-medium" style={statusPill(grant.status)}>{grant.status}</span></div><div className="mt-4 flex flex-wrap gap-2"><Button size="sm" variant="outline" className="rounded-full" style={{ borderColor: COLORS.line, color: COLORS.text, backgroundColor: "white" }} onClick={() => sendAccess(grant.email)}>Resend Access</Button><Button size="sm" variant="outline" className="rounded-full" style={{ borderColor: "#fecaca", color: COLORS.danger, backgroundColor: "white" }} onClick={() => revokeAccess(grant.id)}>Revoke</Button></div></div>)}</div></CardContent></Card>
      </div>
    </div>
  );
}

export default function VeritasAtlasApiLandingPage() {
  const [showAccessModal, setShowAccessModal] = useState(false);
  const [page, setPage] = useState("home");
  return (
    <div className="min-h-screen" style={{ backgroundColor: COLORS.bg }}>
      <header className="border-b" style={{ backgroundColor: COLORS.navy, borderColor: "rgba(255,255,255,0.08)" }}>
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white font-bold" style={{ color: COLORS.navy }}>AT</div>
            <div>
              <div className="text-lg font-semibold text-white">Veritas Atlas API</div>
              <div className="text-sm text-blue-100/90">Dataset registry and validation API</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => setPage("home")} className="hidden rounded-full px-4 py-2 text-sm font-medium md:inline-flex" style={{ backgroundColor: page === "home" ? "white" : "rgba(255,255,255,0.12)", color: page === "home" ? COLORS.navy : "white", border: "1px solid rgba(255,255,255,0.18)" }}>Home</button>
            <button onClick={() => setPage("access-control")} className="hidden rounded-full px-4 py-2 text-sm font-medium md:inline-flex" style={{ backgroundColor: page === "access-control" ? "white" : "rgba(255,255,255,0.12)", color: page === "access-control" ? COLORS.navy : "white", border: "1px solid rgba(255,255,255,0.18)" }}>Access Control</button>
            <Button className="rounded-full flex items-center gap-2" style={{ backgroundColor: "white", color: COLORS.navy }}><Github className="h-4 w-4" />GitHub</Button>
            <Button onClick={() => setShowAccessModal(true)} className="rounded-full" style={{ backgroundColor: "rgba(255,255,255,0.15)", color: "white", border: "1px solid rgba(255,255,255,0.2)" }}>Get API Access</Button>
          </div>
        </div>
      </header>
      <main>
        {page === "home" ? (
          <div className="mx-auto max-w-6xl px-6 py-12">
            <section>
              <Card className="rounded-3xl border shadow-sm" style={{ borderColor: COLORS.line, backgroundColor: "white" }}>
                <CardContent className="p-8 md:p-10">
                  <h1 className="max-w-3xl text-4xl font-semibold leading-tight md:text-5xl" style={{ color: COLORS.text }}>A simple API for managing validated biomedical datasets.</h1>
                  <p className="mt-5 max-w-2xl text-base leading-7 md:text-lg" style={{ color: COLORS.muted }}>Veritas Atlas manages Pennsieve-backed dataset registration, validation, access control, and controlled staging while Veritas handles benchmarking.</p>
                </CardContent>
              </Card>
            </section>
            <section className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
              {features.map((feature) => {
                const Icon = feature.icon;
                return (
                  <Card key={feature.title} className="rounded-3xl border shadow-sm" style={{ borderColor: COLORS.line, backgroundColor: "white" }}>
                    <CardContent className="p-6">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl" style={{ backgroundColor: COLORS.navySoft }}><Icon className="h-6 w-6" style={{ color: COLORS.navy }} /></div>
                      <h3 className="mt-5 text-lg font-semibold" style={{ color: COLORS.text }}>{feature.title}</h3>
                      <p className="mt-3 text-sm leading-6" style={{ color: COLORS.muted }}>{feature.text}</p>
                    </CardContent>
                  </Card>
                );
              })}
            </section>
          </div>
        ) : <AccessControlPage />}
      </main>
      <AccessRequestModal open={showAccessModal} onClose={() => setShowAccessModal(false)} />
    </div>
  );
}
