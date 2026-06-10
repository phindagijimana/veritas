import React, { useCallback, useEffect, useState } from "react";

import {
  clearAuthToken,
  fetchAuthMode,
  fetchCurrentUser,
  getAuthToken,
  login as apiLogin,
  register as apiRegister,
} from "../api/veritasClient.js";

const PANEL_STYLE = {
  width: "100%",
  maxWidth: "26rem",
  padding: "2rem",
  borderRadius: "1rem",
  background: "#fff",
  boxShadow: "0 10px 30px rgba(15, 47, 107, 0.12)",
  border: "1px solid #d7e2f2",
};

const PAGE_STYLE = {
  minHeight: "100vh",
  background: "#f6f9fe",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "1.5rem",
  fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif",
  color: "#16325c",
};

function Field({ label, type = "text", value, onChange, autoComplete, autoFocus }) {
  return (
    <label style={{ display: "block", marginBottom: "0.75rem" }}>
      <div style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>{label}</div>
      <input
        type={type}
        value={value}
        autoComplete={autoComplete}
        autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%",
          padding: "0.55rem 0.7rem",
          fontSize: "0.95rem",
          border: "1px solid #d7e2f2",
          borderRadius: "0.5rem",
          outline: "none",
        }}
      />
    </label>
  );
}

/**
 * LoginGate
 * --------
 * Wraps the app. On mount checks /auth/mode. When auth is enabled and
 * no valid token is present, renders a login/register screen. On success,
 * passes { currentUser, onLogout } to children as a render prop.
 *
 *   <LoginGate>{({ currentUser, onLogout }) => <App user={currentUser} onLogout={onLogout} />}</LoginGate>
 *
 * When auth is disabled (dev mode), it transparently renders children with currentUser=null.
 */
export default function LoginGate({ children }) {
  const [status, setStatus] = useState("checking"); // checking | ready | login
  const [authEnabled, setAuthEnabled] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [mode, setMode] = useState("login"); // login | register
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const bootstrap = useCallback(async () => {
    setError(null);
    const modeRes = await fetchAuthMode();
    if (!modeRes.ok) {
      // API unreachable or misconfigured: surface as login screen with disabled hint.
      setStatus("login");
      setAuthEnabled(true);
      setError(modeRes.message || "Cannot reach Veritas API.");
      return;
    }
    const enabled = Boolean(modeRes.data?.enabled);
    setAuthEnabled(enabled);
    if (!enabled) {
      setStatus("ready");
      setCurrentUser(null);
      return;
    }
    if (!getAuthToken()) {
      setStatus("login");
      return;
    }
    const me = await fetchCurrentUser();
    if (me.ok) {
      setCurrentUser(me.data);
      setStatus("ready");
    } else {
      // Stale / invalid token — clear and ask to log in again.
      clearAuthToken();
      setStatus("login");
      if (me.status && me.status !== 401) setError(me.message);
    }
  }, []);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const submit = useCallback(
    async (e) => {
      e?.preventDefault?.();
      if (!email || !password) {
        setError("Email and password are required.");
        return;
      }
      setSubmitting(true);
      setError(null);
      const res =
        mode === "login"
          ? await apiLogin(email, password)
          : await apiRegister(email, password, fullName);
      setSubmitting(false);
      if (!res.ok) {
        setError(res.message || (mode === "login" ? "Login failed." : "Registration failed."));
        return;
      }
      const user = res.data?.user || null;
      setCurrentUser(user);
      setStatus("ready");
    },
    [email, password, fullName, mode],
  );

  const onLogout = useCallback(() => {
    clearAuthToken();
    setCurrentUser(null);
    setEmail("");
    setPassword("");
    setFullName("");
    setMode("login");
    setError(null);
    setStatus("login");
  }, []);

  if (status === "checking") {
    return (
      <div style={PAGE_STYLE}>
        <div style={{ ...PANEL_STYLE, textAlign: "center" }}>Loading…</div>
      </div>
    );
  }

  if (status === "login") {
    return (
      <div style={PAGE_STYLE}>
        <form style={PANEL_STYLE} onSubmit={submit}>
          <h1 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.25rem" }}>
            {mode === "login" ? "Sign in to Veritas" : "Create your Veritas account"}
          </h1>
          <p style={{ fontSize: "0.85rem", color: "#5e7394", marginBottom: "1.25rem" }}>
            {mode === "login"
              ? "Use the credentials provided by your Veritas administrator."
              : "New accounts are created as researchers; admins are assigned by your administrator."}
          </p>
          <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" autoFocus />
          {mode === "register" && (
            <Field label="Full name (optional)" value={fullName} onChange={setFullName} autoComplete="name" />
          )}
          <Field
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
          {error && (
            <div
              role="alert"
              style={{
                background: "#fef2f2",
                color: "#991b1b",
                padding: "0.6rem 0.75rem",
                borderRadius: "0.5rem",
                fontSize: "0.85rem",
                marginBottom: "0.75rem",
              }}
            >
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={submitting}
            style={{
              width: "100%",
              padding: "0.65rem 1rem",
              borderRadius: "0.6rem",
              background: submitting ? "#94a3b8" : "#0f2f6b",
              color: "#fff",
              fontWeight: 600,
              border: "none",
              cursor: submitting ? "wait" : "pointer",
            }}
          >
            {submitting ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
          <div style={{ marginTop: "0.9rem", textAlign: "center", fontSize: "0.85rem" }}>
            {mode === "login" ? (
              <button
                type="button"
                onClick={() => {
                  setMode("register");
                  setError(null);
                }}
                style={{ background: "none", border: "none", color: "#0f2f6b", cursor: "pointer", fontWeight: 600 }}
              >
                Need an account? Register
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setMode("login");
                  setError(null);
                }}
                style={{ background: "none", border: "none", color: "#0f2f6b", cursor: "pointer", fontWeight: 600 }}
              >
                Already have an account? Sign in
              </button>
            )}
          </div>
        </form>
      </div>
    );
  }

  // status === "ready"
  return children({ currentUser, onLogout, authEnabled });
}
