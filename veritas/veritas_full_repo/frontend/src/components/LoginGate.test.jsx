import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LoginGate from "./LoginGate.jsx";
import { clearAuthToken } from "../api/veritasClient.js";

const ORIG_FETCH = globalThis.fetch;

function mockAuthMode(enabled) {
  return Promise.resolve({
    ok: true,
    status: 200,
    statusText: "OK",
    text: () => Promise.resolve(JSON.stringify({ data: { enabled, mode: "local" } })),
  });
}

describe("LoginGate", () => {
  beforeEach(() => {
    clearAuthToken();
  });
  afterEach(() => {
    globalThis.fetch = ORIG_FETCH;
  });

  it("renders children transparently when auth is disabled", async () => {
    globalThis.fetch = vi.fn(() => mockAuthMode(false));

    render(
      <LoginGate>{({ currentUser }) => <div>App for {String(currentUser)}</div>}</LoginGate>,
    );

    expect(await screen.findByText(/App for null/)).toBeInTheDocument();
  });

  it("shows the login form when auth is enabled and no token is stored", async () => {
    globalThis.fetch = vi.fn(() => mockAuthMode(true));

    render(<LoginGate>{() => <div>should not appear</div>}</LoginGate>);

    expect(await screen.findByRole("heading", { name: /sign in to veritas/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText("should not appear")).not.toBeInTheDocument();
    });
  });
});
