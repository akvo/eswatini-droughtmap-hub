"use client";

import { useState, useMemo } from "react";
import { Input, Select, Button, Switch, message } from "antd";
import {
  MailOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
} from "@ant-design/icons";
import Link from "next/link";
import CWHeader from "@/components/CitizenWeather/CWHeader";
import {
  INKHUNDLA_OPTIONS,
  AEZ_BY_INKHUNDLA,
  REGION_BY_INKHUNDLA,
  SENSOR_OPTIONS,
  STATION_TYPES,
  ADMIN_USERS,
} from "@/static/mocks/citizen-weather";

const { TextArea } = Input;

const AddStationPage = () => {
  const [stationName, setStationName] = useState("Sithobela Community Station");
  const [inkhundla, setInkhundla] = useState("Sithobela");
  const [lat, setLat] = useState("-26.6812");
  const [lng, setLng] = useState("31.7245");
  const [sensors, setSensors] = useState([
    "min_temp",
    "max_temp",
    "rain_gauge",
    "soil_moisture",
  ]);
  const [stationType, setStationType] = useState("Davis Vantage Pro2");
  const [observerName, setObserverName] = useState("Nomsa Simelane");
  const [observerEmail, setObserverEmail] = useState(
    "nomsa.simelane@example.sz"
  );
  const [phone, setPhone] = useState("+268 76 12 3456");
  const [language, setLanguage] = useState("en");
  const [adminNotes, setAdminNotes] = useState(
    "Chairs the Inkhundla DRMC. Best contacted in the mornings."
  );
  const [assignedAdmin, setAssignedAdmin] = useState(ADMIN_USERS[0]);
  const [sendWelcome, setSendWelcome] = useState(true);

  const region = useMemo(
    () => REGION_BY_INKHUNDLA[inkhundla] || "",
    [inkhundla]
  );
  const aez = useMemo(
    () => AEZ_BY_INKHUNDLA[inkhundla] || "",
    [inkhundla]
  );

  const inkhundlaSelectOptions = INKHUNDLA_OPTIONS.map((group) => ({
    label: group.label,
    options: group.options.map((ink) => ({ label: ink, value: ink })),
  }));

  const toggleSensor = (key) => {
    setSensors((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key]
    );
  };

  const handleSave = () => {
    if (!stationName || !inkhundla || !observerName || !observerEmail) {
      message.warning("Please fill in all required fields.");
      return;
    }
    message.success(
      sendWelcome
        ? "Station created and welcome email sent!"
        : "Station created (no email sent)."
    );
  };

  return (
    <div className="w-full h-auto">
      {/* Header */}
      <div className="px-4 sm:px-8 md:px-12 xl:px-20 pt-4 pb-0">
        <div className="mx-auto w-full max-w-[1280px]">
          <CWHeader
            isAdmin
            subtitle="Register a new weather station and its observer"
            userName="Dr Felix Motsa · UNESWA admin"
            userInitials="LO"
          />
        </div>
      </div>

      {/* Hero */}
      <section className="relative overflow-hidden bg-white px-4 pb-24 pt-10 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
        />
        <div className="relative mx-auto w-full max-w-[1280px]">
          <Link
            href="/citizen-weather/admin"
            className="inline-flex items-center gap-1.5 text-sm text-[#3E5EB9] mb-4 hover:underline"
          >
            <ArrowLeftOutlined /> Back to admin
          </Link>
          <h1 className="text-[28px] font-bold leading-10 text-[#333333] mb-2">
            Add station + observer
          </h1>
          <p className="text-sm leading-6 text-[#606060]">
            One observer per station. The observer receives a welcome email with
            their first sign-in link and the monthly reminder from the following
            month onwards.
          </p>
        </div>
      </section>

      {/* Form content */}
      <div className="relative px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <div className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px]">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            {/* Section 1: Station details */}
            <section className="border border-[#eaecf0] bg-white">
              <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6">
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

                <FieldGroup label="Inkhundla" required hint="search or scroll to find">
                  <Select
                    showSearch
                    style={{ width: "100%" }}
                    placeholder="Select the Inkhundla"
                    value={inkhundla || undefined}
                    onChange={setInkhundla}
                    options={inkhundlaSelectOptions}
                    optionFilterProp="label"
                  />
                </FieldGroup>

                <FieldGroup label="Region" hint="auto-filled from Inkhundla">
                  <Input
                    value={region}
                    disabled
                    className="bg-[#f9fafb] italic"
                  />
                </FieldGroup>

                <FieldGroup label="Agro-ecological zone" hint="auto-filled from Inkhundla">
                  <Input
                    value={aez}
                    disabled
                    className="bg-[#f9fafb] italic"
                  />
                </FieldGroup>

                <FieldGroup label="Coordinates" required hint="decimal degrees, WGS84">
                  <div className="grid grid-cols-2 gap-2.5">
                    <Input
                      placeholder="Latitude · e.g. -26.6812"
                      value={lat}
                      onChange={(e) => setLat(e.target.value)}
                    />
                    <Input
                      placeholder="Longitude · e.g. 31.7245"
                      value={lng}
                      onChange={(e) => setLng(e.target.value)}
                    />
                  </div>
                  <div className="mt-3 rounded-lg bg-gradient-to-br from-[#dbeafe] to-[#fef3c7] h-[120px] flex items-center justify-center relative">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="#FF4D4F" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5S10.62 6.5 12 6.5s2.5 1.12 2.5 2.5S13.38 11.5 12 11.5z" />
                    </svg>
                    <div className="absolute bottom-0 left-0 right-0 bg-white/80 backdrop-blur-sm px-3 py-1.5 flex items-center justify-between text-xs text-[#606060]">
                      <span className="font-mono">
                        {lat || "\u2014"}, {lng || "\u2014"}
                      </span>
                      {lat && lng && (
                        <span className="text-[#12b76a] font-semibold inline-flex items-center gap-1">
                          <CheckCircleOutlined /> inside Eswatini
                        </span>
                      )}
                    </div>
                  </div>
                </FieldGroup>

                <FieldGroup label="Sensors this station has" hint="determines which fields the observer sees">
                  <div className="flex flex-col gap-2">
                    {SENSOR_OPTIONS.map((s) => {
                      const active = sensors.includes(s.key);
                      return (
                        <button
                          key={s.key}
                          type="button"
                          className={`flex items-center justify-between py-3 px-4 border rounded-lg cursor-pointer transition-all text-left ${
                            active
                              ? "border-[#3E5EB9]"
                              : "border-[#eaecf0]"
                          }`}
                          onClick={() => toggleSensor(s.key)}
                        >
                          <span className="text-sm text-[#333333]">
                            {s.label}
                          </span>
                          <span
                            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                              active
                                ? "border-[#3E5EB9]"
                                : "border-[#d2d2d2]"
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
                    options={STATION_TYPES.map((t) => ({ label: t, value: t }))}
                  />
                </FieldGroup>
              </div>
            </section>

            {/* Section 2: Observer details */}
            <section className="border border-[#eaecf0] bg-white">
              <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-[#3E5EB9] text-white text-xs font-bold flex items-center justify-center">
                    2
                  </span>
                  <h2 className="text-base font-semibold text-[#333333]">
                    Observer details
                  </h2>
                </div>
                <p className="text-xs text-[#606060] mt-1 ml-8">
                  The person who will submit monthly readings. One observer per station.
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

                <FieldGroup label="Email address" required hint="this is where reminders + sign-in links go">
                  <Input
                    type="email"
                    placeholder="e.g. name@example.sz"
                    value={observerEmail}
                    onChange={(e) => setObserverEmail(e.target.value)}
                  />
                </FieldGroup>

                <FieldGroup label="Phone number" hint="optional · used only as fallback">
                  <Input
                    placeholder="e.g. +268 76 XX XXXX"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </FieldGroup>

                <FieldGroup label="Preferred language for reminders">
                  <div className="flex gap-2">
                    {[
                      { key: "en", label: "EN English" },
                      { key: "ss", label: "SS siSwati" },
                    ].map((lang) => (
                      <button
                        key={lang.key}
                        type="button"
                        className={`flex-1 py-2 px-3 border rounded-lg text-center cursor-pointer text-xs transition-all select-none ${
                          language === lang.key
                            ? "border-[#3E5EB9] bg-[#f0f4ff] text-[#333333] font-semibold"
                            : "border-[#eaecf0] bg-white text-[#606060]"
                        }`}
                        onClick={() => setLanguage(lang.key)}
                      >
                        {lang.label}
                      </button>
                    ))}
                  </div>
                </FieldGroup>

                <FieldGroup label="Notes about this observer" hint="optional · admin-only">
                  <TextArea
                    rows={3}
                    placeholder="e.g. teaches at the local school, best contacted after 15:00"
                    value={adminNotes}
                    onChange={(e) => setAdminNotes(e.target.value)}
                  />
                </FieldGroup>

                <FieldGroup label="Assigned admin" hint="who follows up if this observer stops reporting">
                  <Select
                    style={{ width: "100%" }}
                    value={assignedAdmin}
                    onChange={setAssignedAdmin}
                    options={ADMIN_USERS.map((a) => ({ label: a, value: a }))}
                  />
                </FieldGroup>
              </div>
            </section>
          </div>

          {/* Welcome email preview */}
          <section className="border border-[#eaecf0] bg-white mb-4">
            <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6 flex items-center gap-2">
              <MailOutlined className="text-[#606060]" />
              <h2 className="text-base font-semibold text-[#333333]">
                Welcome email preview
              </h2>
            </div>
            <div className="p-4 sm:p-6">
              <p className="text-xs text-[#606060] mb-4">
                This is what <b>{observerName || "the observer"}</b> will receive as
                soon as you click &ldquo;Save + send welcome email&rdquo;.
              </p>
              <div className="border border-[#eaecf0] rounded-lg p-4 text-xs text-[#333333] leading-relaxed">
                <div className="font-bold text-[#333333] mb-1.5">
                  Welcome to Citizen Science Weather &mdash; your first sign-in link
                </div>
                <div>Sanibonani {observerName?.split(" ")[0] || "\u2014"},</div>
                <br />
                <div>
                  You&apos;ve been registered as the observer for the{" "}
                  <b>{stationName || "\u2014"}</b> in {region || "\u2014"}. On the 1st of every
                  month, we&apos;ll email you a link to submit that month&apos;s
                  weather reading &mdash; no password to remember, just click and fill in
                  what your station measured.
                </div>
                <br />
                <div>
                  To confirm your account and set up your first monthly submission,
                  click below:
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
              <b>Save + send welcome email</b> creates the observer + station and
              sends the confirmation link above. You can also save the station
              without an observer if the observer will be assigned later.
            </span>
            <div className="flex items-center gap-2.5 text-xs text-[#606060]">
              <span>Send welcome email now</span>
              <Switch
                checked={sendWelcome}
                onChange={setSendWelcome}
              />
            </div>
            <Link href="/citizen-weather/admin">
              <Button>Cancel</Button>
            </Link>
            <Button type="primary" onClick={handleSave}>
              {sendWelcome ? "Save + send welcome email" : "Save station"}
            </Button>
          </div>
        </div>
      </div>
    </div>
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
