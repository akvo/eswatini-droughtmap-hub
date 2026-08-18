"use client";

import { useState, useEffect } from "react";
import { Modal, Input, Select, Switch, message } from "antd";
import { api } from "@/lib";
import { SENSOR_OPTIONS, STATION_TYPES } from "@/static/citizen-weather";

const sensorChoices = SENSOR_OPTIONS.map((s) => ({
  label: s.label,
  value: s.key,
}));

const stationTypeChoices = STATION_TYPES.map((t) => ({
  label: t,
  value: t === "Not specified" ? "" : t,
}));

export const StationEditModal = ({ open, onClose, station, onSaved }) => {
  const [loading, setLoading] = useState(false);
  const [stationName, setStationName] = useState("");
  const [stationType, setStationType] = useState("");
  const [sensors, setSensors] = useState([]);
  const [administrationId, setAdministrationId] = useState(null);
  const [administrations, setAdministrations] = useState([]);

  useEffect(() => {
    if (open && station) {
      setStationName(station.label || "");
      setStationType(station.station_type || "");
      setSensors(station.sensors || []);
      setAdministrationId(station.key ?? null);
    }
  }, [open, station]);

  // One active observer per Inkhundla (uniq_observer_per_administration), so
  // the only selectable targets are the free ones plus the station's own.
  useEffect(() => {
    if (!open) return;
    Promise.all([
      api("GET", "/iks/administrations"),
      api("GET", "/weather/citizen-science/stations"),
    ])
      .then(([res, network]) => {
        const data = Array.isArray(res) ? res : res.data || [];
        const taken = new Set((network?.data || []).map((row) => row.key));
        setAdministrations(
          data.filter((a) => !taken.has(a.id) || a.id === station?.key),
        );
      })
      .catch((err) => {
        console.error(err);
        message.error("Failed to load Inkhundla list.");
      });
  }, [open, station?.key]);

  const moved = administrationId && administrationId !== station?.key;
  const region =
    administrations.find((a) => a.id === administrationId)?.region || "";

  const handleOk = async () => {
    setLoading(true);
    try {
      const res = await api(
        "PATCH",
        `/weather/citizen-science/stations/${station.key}`,
        {
          station_name: stationName,
          station_type: stationType,
          sensors,
          administration_id: administrationId,
        },
      );
      message.success(
        moved
          ? "Station moved. Readings stay with the previous Inkhundla."
          : "Station updated.",
      );
      // Moving re-keys the station, so hand back the new id — the caller's
      // current URL points at the old Inkhundla and would 404 on refetch.
      onSaved?.(res?.administration_id);
      onClose();
    } catch (err) {
      console.error(err);
      message.error(err?.message || "Failed to update station.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Edit station"
      open={open}
      onCancel={onClose}
      onOk={handleOk}
      okText="Save"
      confirmLoading={loading}
      destroyOnClose
    >
      <div className="flex flex-col gap-4 py-2">
        <div>
          <label className="text-sm font-medium text-[#333] block mb-1">
            Station name
          </label>
          <Input
            value={stationName}
            onChange={(e) => setStationName(e.target.value)}
            maxLength={120}
          />
        </div>
        <div>
          <label className="text-sm font-medium text-[#333] block mb-1">
            Inkhundla
            <span className="text-xs text-[#606060] font-normal ml-1">
              &middot; only Tinkhundla without a station are listed
            </span>
          </label>
          <Select
            showSearch
            style={{ width: "100%" }}
            value={administrationId || undefined}
            onChange={setAdministrationId}
            optionFilterProp="label"
            options={administrations.map((a) => ({
              label: a.name,
              value: a.id,
            }))}
          />
          {region && (
            <div className="text-xs text-[#606060] mt-1">{region} region</div>
          )}
          {moved && (
            <div className="text-xs text-[#d46b08] mt-1">
              Moving this station leaves its reading history with the previous
              Inkhundla — readings belong to the Inkhundla they were reported
              for, not to the station.
            </div>
          )}
        </div>
        <div>
          <label className="text-sm font-medium text-[#333] block mb-1">
            Station type
          </label>
          <Select
            style={{ width: "100%" }}
            value={stationType}
            onChange={setStationType}
            options={stationTypeChoices}
          />
        </div>
        <div>
          <label className="text-sm font-medium text-[#333] block mb-1">
            Sensors
          </label>
          <Select
            mode="multiple"
            style={{ width: "100%" }}
            value={sensors}
            onChange={setSensors}
            options={sensorChoices}
          />
        </div>
      </div>
    </Modal>
  );
};

export const ObserverEditModal = ({ open, onClose, station, onSaved }) => {
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    if (open && station) {
      const obs = station.observer || {};
      setName(obs.name || "");
      setEmail(obs.email || "");
    }
  }, [open, station]);

  const handleOk = async () => {
    setLoading(true);
    try {
      await api("PATCH", `/weather/citizen-science/stations/${station.key}`, {
        name,
        email,
      });
      message.success("Observer details updated.");
      onSaved?.();
      onClose();
    } catch (err) {
      message.error(err?.message || "Failed to update observer.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Edit observer"
      open={open}
      onCancel={onClose}
      onOk={handleOk}
      okText="Save"
      confirmLoading={loading}
      destroyOnClose
    >
      <div className="flex flex-col gap-4 py-2">
        <div>
          <label className="text-sm font-medium text-[#333] block mb-1">
            Name
          </label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={100}
          />
        </div>
        <div>
          <label className="text-sm font-medium text-[#333] block mb-1">
            Email
          </label>
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
};

export const ReassignObserverModal = ({ open, onClose, station, onSaved }) => {
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [sendEmail, setSendEmail] = useState(true);

  useEffect(() => {
    if (open) {
      setName("");
      setEmail("");
      setSendEmail(true);
    }
  }, [open]);

  const handleOk = async () => {
    if (!name.trim() || !email.trim()) {
      message.warning("Name and email are required.");
      return;
    }
    setLoading(true);
    try {
      await api("POST", `/weather/citizen-science/stations/${station.key}`, {
        name,
        email,
        send_welcome_email: sendEmail,
      });
      message.success("Station reassigned to new observer.");
      onSaved?.();
      onClose();
    } catch (err) {
      message.error(err?.message || "Failed to reassign observer.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Reassign observer"
      open={open}
      onCancel={onClose}
      onOk={handleOk}
      okText="Reassign"
      confirmLoading={loading}
      destroyOnClose
    >
      <p className="text-xs text-[#606060] mb-4">
        The current observer will be archived and can no longer sign in. Their
        submitted readings are kept.
      </p>
      <div className="flex flex-col gap-4 py-2">
        <div>
          <label className="text-sm font-medium text-[#333] block mb-1">
            New observer name
          </label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={100}
            placeholder="e.g. Thabo Nkosi"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-[#333] block mb-1">
            Email
          </label>
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="e.g. thabo@example.sz"
          />
        </div>
        <div className="flex items-center gap-2">
          <Switch checked={sendEmail} onChange={setSendEmail} size="small" />
          <span className="text-sm text-[#333]">
            Send welcome email with sign-in link
          </span>
        </div>
      </div>
    </Modal>
  );
};
