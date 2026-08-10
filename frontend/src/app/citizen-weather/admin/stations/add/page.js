"use client";

import { useState, useEffect, useCallback } from "react";
import { Input, Select, Button, Switch, message, Spin } from "antd";
import { MailOutlined, ArrowLeftOutlined } from "@ant-design/icons";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Can, PageHeader } from "@/components";
import { api } from "@/lib";
import { SENSOR_OPTIONS, STATION_TYPES } from "@/static/citizen-weather";

const AddStationPage = () => {
  const router = useRouter();
  const [stationName, setStationName] = useState("");
  const [administrationId, setAdministrationId] = useState(null);
  const [sensors, setSensors] = useState([]);
  const [stationType, setStationType] = useState("Not specified");
  const [observerName, setObserverName] = useState("");
  const [observerEmail, setObserverEmail] = useState("");
  const [sendWelcome, setSendWelcome] = useState(true);
  const [saving, setSaving] = useState(false);

  const [administrations, setAdministrations] = useState([]);
  const [loadingAdministrations, setLoadingAdministrations] = useState(true);

  // Selected administration details for display
  const selectedAdmin = administrations.find((a) => a.id === administrationId);
  const region = selectedAdmin?.region || "";

  const fetchAdministrations = useCallback(async () => {
    setLoadingAdministrations(true);
    try {
      // One observer per Inkhundla — the backend rejects a second one with
      // "This Inkhundla already has an active observer." The admin network
      // rows are keyed by administration_id, so they are the taken set:
      // drop those instead of letting the admin discover it on save.
      const [res, network] = await Promise.all([
        api("GET", "/iks/administrations"),
        api("GET", "/weather/citizen-science/stations"),
      ]);
      const data = Array.isArray(res) ? res : res.data || [];
      const taken = new Set((network?.data || []).map((row) => row.key));
      setAdministrations(data.filter((a) => !taken.has(a.id)));
    } catch (err) {
      console.error(err);
      message.error("Failed to load Inkhundla list.");
    } finally {
      setLoadingAdministrations(false);
    }
  }, []);

  useEffect(() => {
    fetchAdministrations();
  }, [fetchAdministrations]);

  // Group administrations by region for the Select dropdown
  const inkhundlaSelectOptions = administrations.reduce((groups, admin) => {
    const regionLabel = `${admin.region} region`;
    let group = groups.find((g) => g.label === regionLabel);
    if (!group) {
      group = { label: regionLabel, options: [] };
      groups.push(group);
    }
    group.options.push({ label: admin.name, value: admin.id });
    return groups;
  }, []);

  const toggleSensor = (key) => {
    setSensors((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key],
    );
  };

  const handleSave = async () => {
    if (!stationName || !administrationId || !observerName || !observerEmail) {
      message.warning("Please fill in all required fields.");
      return;
    }
    setSaving(true);
    try {
      await api("POST", "/weather/citizen-science/stations", {
        name: observerName,
        email: observerEmail,
        administration_id: administrationId,
        station_name: stationName,
        sensors,
        station_type: stationType,
        send_welcome_email: sendWelcome,
      });
      message.success(
        sendWelcome
          ? "Station created and welcome email sent!"
          : "Station created (no email sent).",
      );
      router.push("/citizen-weather/admin");
    } catch (err) {
      // api() flattens the DRF 400 body ("A user with this email already
      // exists.", "This Inkhundla already has an active observer.") into the
      // error message, so show it rather than guessing from keywords.
      console.error(err);
      message.error(
        err?.message || "Failed to create station. Please try again.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <Can I="create" a="CitizenScience">
      <div className="w-full h-auto">
        <PageHeader
          title="Add station + observer"
          description="One observer per station. The observer receives a welcome email with their first sign-in link and the monthly reminder from the following month onwards."
          actions={
            <Link href="/citizen-weather/admin">
              <Button icon={<ArrowLeftOutlined />}>Back to admin</Button>
            </Link>
          }
        />

        <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
          <div
            aria-hidden
            className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
          />
          <div className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px]">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
              {/* Section 1: Station details */}
              <section className="border border-cardBorder bg-white">
                <div className="border-b border-cardBorder px-4 py-4 sm:px-6">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-[#3E5EB9] text-white text-xs font-bold flex items-center justify-center">
                      1
                    </span>
                    <h2 className="text-base font-semibold text-[#333333]">
                      Weather station details
                    </h2>
                  </div>
                  <p className="text-xs text-[#606060] mt-1 ml-8">
                    Where the station is and what it can measure.
                  </p>
                </div>
                <div className="p-4 sm:p-6 flex flex-col gap-5">
                  <FieldGroup label="Station name" required>
                    <Input
                      placeholder="e.g. Big Bend Community Weather Station"
                      value={stationName}
                      onChange={(e) => setStationName(e.target.value)}
                    />
                  </FieldGroup>

                  <FieldGroup
                    label="Inkhundla"
                    required
                    hint="only Inkhundla without an observer are listed"
                  >
                    {loadingAdministrations ? (
                      <Spin size="small" />
                    ) : (
                      <Select
                        showSearch
                        style={{ width: "100%" }}
                        placeholder="Select the Inkhundla"
                        value={administrationId || undefined}
                        onChange={setAdministrationId}
                        options={inkhundlaSelectOptions}
                        optionFilterProp="label"
                      />
                    )}
                  </FieldGroup>

                  <FieldGroup label="Region" hint="auto-filled from Inkhundla">
                    <Input
                      value={region}
                      disabled
                      className="bg-[#f9fafb] italic"
                    />
                  </FieldGroup>

                  <FieldGroup
                    label="Sensors this station has"
                    hint="determines which fields the observer sees"
                  >
                    <div className="flex flex-col gap-2">
                      {SENSOR_OPTIONS.map((s) => {
                        const active = sensors.includes(s.key);
                        return (
                          <button
                            key={s.key}
                            type="button"
                            className={`flex items-center justify-between py-3 px-4 border rounded-lg cursor-pointer transition-all text-left ${
                              active ? "border-[#3E5EB9]" : "border-cardBorder"
                            }`}
                            onClick={() => toggleSensor(s.key)}
                          >
                            <span className="text-sm text-[#333333]">
                              {s.label}
                            </span>
                            <span
                              className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                                active ? "border-[#3E5EB9]" : "border-[#d2d2d2]"
                              }`}
                            >
                              {active && (
                                <span className="w-2.5 h-2.5 rounded-full bg-[#3E5EB9]" />
                              )}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </FieldGroup>

                  <FieldGroup label="Station type or model" hint="optional">
                    <Select
                      style={{ width: "100%" }}
                      value={stationType}
                      onChange={setStationType}
                      options={STATION_TYPES.map((t) => ({
                        label: t,
                        value: t,
                      }))}
                    />
                  </FieldGroup>
                </div>
              </section>

              {/* Section 2: Observer details */}
              <section className="border border-cardBorder bg-white">
                <div className="border-b border-cardBorder px-4 py-4 sm:px-6">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-[#3E5EB9] text-white text-xs font-bold flex items-center justify-center">
                      2
                    </span>
                    <h2 className="text-base font-semibold text-[#333333]">
                      Observer details
                    </h2>
                  </div>
                  <p className="text-xs text-[#606060] mt-1 ml-8">
                    The person who will submit monthly readings. One observer
                    per station.
                  </p>
                </div>
                <div className="p-4 sm:p-6 flex flex-col gap-5">
                  <FieldGroup label="Full name" required>
                    <Input
                      placeholder="e.g. Sipho Dlamini"
                      value={observerName}
                      onChange={(e) => setObserverName(e.target.value)}
                    />
                  </FieldGroup>

                  <FieldGroup
                    label="Email address"
                    required
                    hint="this is where reminders + sign-in links go"
                  >
                    <Input
                      type="email"
                      placeholder="e.g. name@example.sz"
                      value={observerEmail}
                      onChange={(e) => setObserverEmail(e.target.value)}
                    />
                  </FieldGroup>
                </div>
              </section>
            </div>

            {/* Welcome email preview */}
            <section className="border border-cardBorder bg-white mb-4">
              <div className="border-b border-cardBorder px-4 py-4 sm:px-6 flex items-center gap-2">
                <MailOutlined className="text-[#606060]" />
                <h2 className="text-base font-semibold text-[#333333]">
                  Welcome email preview
                </h2>
              </div>
              <div className="p-4 sm:p-6">
                <p className="text-xs text-[#606060] mb-4">
                  This is what <b>{observerName || "the observer"}</b> will
                  receive as soon as you click &ldquo;Save + send welcome
                  email&rdquo;.
                </p>
                <div className="border border-cardBorder rounded-lg p-4 text-xs text-[#333333] leading-relaxed">
                  <div className="font-bold text-[#333333] mb-1.5">
                    Welcome to Citizen Science Weather &mdash; your first
                    sign-in link
                  </div>
                  <div>
                    Sanibonani {observerName?.split(" ")[0] || "\u2014"},
                  </div>
                  <br />
                  <div>
                    You&apos;ve been registered as the observer for the{" "}
                    <b>{stationName || "\u2014"}</b> in {region || "\u2014"}. On
                    the 1st of every month, we&apos;ll email you a link to
                    submit that month&apos;s weather reading &mdash; no password
                    to remember, just click and fill in what your station
                    measured.
                  </div>
                  <br />
                  <div>
                    To confirm your account and set up your first monthly
                    submission, click below:
                  </div>
                  <div className="mt-2">
                    <span className="inline-block px-3.5 py-1.5 bg-[#3E5EB9] text-white text-xs font-semibold">
                      Confirm your account &rarr;
                    </span>
                  </div>
                </div>
              </div>
            </section>

            {/* Bottom actions */}
            <div className="flex flex-wrap items-center gap-3 py-4">
              <span className="text-xs text-[#606060] mr-auto max-w-[400px]">
                <b>Save + send welcome email</b> creates the observer + station
                and sends the confirmation link above. You can also save the
                station without an observer if the observer will be assigned
                later.
              </span>
              <div className="flex items-center gap-2.5 text-xs text-[#606060]">
                <span>Send welcome email now</span>
                <Switch checked={sendWelcome} onChange={setSendWelcome} />
              </div>
              <Link href="/citizen-weather/admin">
                <Button>Cancel</Button>
              </Link>
              <Button type="primary" onClick={handleSave} loading={saving}>
                {sendWelcome ? "Save + send welcome email" : "Save station"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Can>
  );
};

const FieldGroup = ({ label, required, hint, children }) => (
  <div>
    <label className="text-sm font-medium text-[#333333] block mb-1.5">
      {label}
      {required && <span className="text-[#FF4D4F] ml-0.5">*</span>}
      {hint && (
        <span className="text-xs text-[#606060] font-normal ml-1">
          &middot; {hint}
        </span>
      )}
    </label>
    {children}
  </div>
);

export default AddStationPage;
