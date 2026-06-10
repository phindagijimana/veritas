import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearAuthToken,
  getAuthToken,
  login,
  logout,
  setAuthToken,
} from "./veritasClient.js";

const ORIG_FETCH = globalThis.fetch;

function mockJsonResponse(body, { status = 200 } = {}) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Err",
    text: () => Promise.resolve(JSON.stringify(body)),
  });
}

describe("auth token storage", () => {
  afterEach(() => {
    clearAuthToken();
  });

  it("stores, reads, and clears the token", () => {
    expect(getAuthToken()).toBeNull();
    setAuthToken("abc.def.ghi");
    expect(getAuthToken()).toBe("abc.def.ghi");
    clearAuthToken();
    expect(getAuthToken()).toBeNull();
  });

  it("logout() clears the token", () => {
    setAuthToken("xyz");
    logout();
    expect(getAuthToken()).toBeNull();
  });
});

describe("login()", () => {
  beforeEach(() => {
    clearAuthToken();
  });
  afterEach(() => {
    globalThis.fetch = ORIG_FETCH;
  });

  it("persists access_token on successful login", async () => {
    globalThis.fetch = vi.fn(() =>
      mockJsonResponse({
        access_token: "jwt.token.value",
        token_type: "bearer",
        user: { email: "admin@veritas.local", role: "admin" },
      }),
    );

    const res = await login("admin@veritas.local", "pw");
    expect(res.ok).toBe(true);
    expect(getAuthToken()).toBe("jwt.token.value");
  });

  it("returns error and does not store anything on 401", async () => {
    globalThis.fetch = vi.fn(() =>
      mockJsonResponse({ detail: "Invalid email or password." }, { status: 401 }),
    );

    const res = await login("admin@veritas.local", "wrong");
    expect(res.ok).toBe(false);
    expect(res.message).toContain("Invalid");
    expect(getAuthToken()).toBeNull();
  });

  it("attaches Authorization header on subsequent calls when a token is set", async () => {
    setAuthToken("my.jwt");
    const fetchMock = vi.fn(() =>
      mockJsonResponse({ data: { enabled: true, mode: "local" } }),
    );
    globalThis.fetch = fetchMock;

    // Use a function that exercises the wrapper; we don't import the private
    // helper but fetchAuthMode exercises the same path.
    const { fetchAuthMode } = await import("./veritasClient.js");
    await fetchAuthMode();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer my.jwt");
  });
});
