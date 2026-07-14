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
    // Intercept IKS endpoints to return static mock data using the prototype file
    if (url.startsWith("/iks")) {
      try {
        const protoPath = path.join(process.cwd(), "src/static/iks_data.json");
        const rawData = fs.readFileSync(protoPath, "utf-8");
        const proto = JSON.parse(rawData);

        if (url === "/iks/indicators") {
          // Construct the 29 indicators from our config keys
          const indicators = Object.keys(IKS_INDICATOR_CATALOGUE).map(
            (name, index) => ({
              id: index + 1,
              name: name,
            }),
          );
          return resolve(indicators);
        }

        if (url === "/iks/aggregations/net-signal") {
          return resolve({
            weeks: proto.weeks,
            trend: proto.trend,
          });
        }

        if (url === "/iks/aggregations/indicator-counts") {
          // Derive per-indicator submission counts from radar region averages
          const regionAvgs = Object.values(proto.radar).map(
            (arr) => arr.reduce((a, b) => a + b, 0) / arr.length,
          );
          const baseCount = Math.round(
            regionAvgs.reduce((a, b) => a + b, 0) / regionAvgs.length,
          );
          const data = Object.keys(IKS_INDICATOR_CATALOGUE).map((key, i) => ({
            indicator: i + 1,
            code: IKS_INDICATOR_CATALOGUE[key].code,
            indicator_type: IKS_INDICATOR_CATALOGUE[key].type,
            meaning: IKS_INDICATOR_CATALOGUE[key].meaning,
            submission_count: Math.max(1, baseCount + ((i * 7) % 30) - 10),
          }));
          return resolve({ data });
        }

        if (url === "/iks/aggregations/agreement") {
          return resolve({
            agreement: proto.agreement,
          });
        }

        if (url === "/iks/aggregations/soil-trend") {
          return resolve({
            weeks: proto.weeks,
            soil_trend: proto.soil_trend,
            region_map: proto.region_map,
          });
        }

        if (url === "/iks/aggregations/heatmap") {
          return resolve({
            constituencies: proto.constituencies.slice(0, 20),
            weeks: proto.weeks,
            heatmap: proto.heatmap,
          });
        }
      } catch (err) {
        console.error(
          "IKS prototype mock load failed, falling back to network",
          err,
        );
      }
    }

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
