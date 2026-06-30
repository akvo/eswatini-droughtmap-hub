"use server";
import { getSession } from "./auth";

// Server-side calls go straight to the backend, bypassing the Next.js rewrite
// proxy (which resets long-running upstream requests at ~30s). Falls back to
// WEBDOMAIN so existing deployments keep working if BACKEND_URL is unset.
const backendBaseURL = process.env.BACKEND_URL || process.env.WEBDOMAIN;

export const api = (method, url, payload = {}) =>
  new Promise(async (resolve, reject) => {
    const _session = await getSession();
    const headers = {
      "Content-Type": "application/json",
    };
    if (_session) {
      const { token: authToken } = _session;
      headers["Authorization"] = `Bearer ${authToken}`;
    }
    const fetchProps = {
      method,
      headers,
    };
    if (typeof payload === "object" && Object.keys(payload).length) {
      fetchProps["body"] = JSON.stringify(payload);
    }
    try {
      const res = await fetch(`${backendBaseURL}/api/v1${url}`, fetchProps);
      const raw = await res.text();
      let body = null;
      try {
        body = raw ? JSON.parse(raw) : null;
      } catch (_parseErr) {
        // Upstream returned a non-JSON body (e.g. proxy reset / HTML error page).
        return reject(
          new Error(
            `Non-JSON response from ${url} (HTTP ${res.status}): ` +
              `${raw.slice(0, 200)}`
          )
        );
      }
      return resolve(body);
    } catch (err) {
      return reject(err);
    }
  });
