"use server";

import fs from "fs";
import path from "path";
import { getSession } from "./auth";
import { IKS_INDICATOR_CATALOGUE } from "@/static/config";

// Server-side calls go straight to the backend, bypassing the Next.js rewrite
// proxy (which resets long-running upstream requests at ~30s). Falls back to
// WEBDOMAIN so existing deployments keep working if BACKEND_URL is unset.
const backendBaseURL = process.env.BACKEND_URL || process.env.WEBDOMAIN;

export const api = (method, url, payload = {}) =>
  new Promise(async (resolve, reject) => {
    const _session = await getSession();
    const isFormData =
      typeof FormData !== "undefined" && payload instanceof FormData;
    const headers = {};
    if (!isFormData) {
      headers["Content-Type"] = "application/json";
    }
    if (_session) {
      const { token: authToken } = _session;
      headers["Authorization"] = `Bearer ${authToken}`;
    }
    const fetchProps = {
      method,
      headers,
    };
    if (isFormData) {
      fetchProps["body"] = payload;
    } else if (typeof payload === "object" && Object.keys(payload).length) {
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
              `${raw.slice(0, 200)}`,
          ),
        );
      }
      return resolve(body);
    } catch (err) {
      return reject(err);
    }
  });

export const apiText = (method, url, payload = {}) =>
  new Promise(async (resolve, reject) => {
    const _session = await getSession();
    const headers = {};
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
      if (!res.ok) {
        return reject(new Error(`HTTP ${res.status}: ${raw.slice(0, 200)}`));
      }
      return resolve(raw);
    } catch (err) {
      return reject(err);
    }
  });

export const getSourceFileBase64 = async (activityId) => {
  const _session = await getSession();
  const headers = {};
  if (_session) {
    const { token: authToken } = _session;
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  const res = await fetch(
    `${backendBaseURL}/api/v1/activity/${activityId}/source-file`,
    { headers },
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const arrayBuffer = await res.arrayBuffer();
  const base64 = Buffer.from(arrayBuffer).toString("base64");
  const contentType =
    res.headers.get("content-type") || "application/octet-stream";

  // Extract filename from Content-Disposition header if present
  const contentDisposition = res.headers.get("content-disposition");
  let filename = "source_file";
  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
    if (filenameMatch) {
      filename = filenameMatch[1];
    }
  }

  return { base64, contentType, filename };
};
