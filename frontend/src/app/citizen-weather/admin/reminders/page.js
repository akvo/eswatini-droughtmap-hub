"use client";

import { useMemo, useState } from "react";
import { Input, Select, Button } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import Link from "next/link";
import { PageHeader } from "@/components";
import { MONTH_NAMES, formatDate } from "@/components/CitizenWeather/utils";

const NextReminderPreview = ({ day, time, deadline, followUp1, followUp2 }) => {
  const preview = useMemo(() => {
    const now = new Date();
    // Next reminder is the 1st (or chosen day) of next month
    const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    const reminderDay =
      day === "last"
        ? new Date(nextMonth.getFullYear(), nextMonth.getMonth(), 0).getDate()
        : Math.min(parseInt(day, 10) || 1, 28);
    const reminderDate =
      day === "last"
        ? new Date(
            nextMonth.getFullYear(),
            nextMonth.getMonth() - 1,
            reminderDay,
          )
        : new Date(nextMonth.getFullYear(), nextMonth.getMonth(), reminderDay);
    const reportMonth = MONTH_NAMES[now.getMonth()];

    const deadlineDays = deadline === "none" ? null : parseInt(deadline, 10);
    const fu1Days = followUp1 === "off" ? null : parseInt(followUp1, 10);
    const fu2Days = followUp2 === "off" ? null : parseInt(followUp2, 10);

    let fu1Date = null;
    let fu2Date = null;
    if (deadlineDays != null) {
      const deadlineDate = new Date(reminderDate);
      deadlineDate.setDate(deadlineDate.getDate() + deadlineDays);
      if (fu1Days != null) {
        fu1Date = new Date(deadlineDate);
        fu1Date.setDate(fu1Date.getDate() + fu1Days);
      }
      if (fu2Days != null) {
        fu2Date = new Date(deadlineDate);
        fu2Date.setDate(fu2Date.getDate() + fu2Days);
      }
    }

    return { reminderDate, reportMonth, fu1Date, fu2Date };
  }, [day, deadline, followUp1, followUp2]);

  return (
    <section className="border border-cardBorder bg-white mb-4">
      <div className="border-b border-cardBorder px-4 py-4 sm:px-6">
        <h2 className="text-base font-semibold text-[#333333]">
          Next scheduled reminder
        </h2>
        <p className="text-xs text-[#606060] mt-1">
          Based on your current settings.
        </p>
      </div>
      <div className="p-4 sm:p-6">
        <div className="border border-cardBorder rounded-lg p-4 text-sm text-[#333333] leading-relaxed">
          <b className="text-[#333333]">
            {formatDate(preview.reminderDate)} &middot; {time} SAST
          </b>{" "}
          &rarr; observers across all 4 regions receive their{" "}
          {preview.reportMonth} reminder.
          {(preview.fu1Date || preview.fu2Date) && (
            <div className="text-xs text-[#606060] mt-2 leading-relaxed">
              {preview.fu1Date && (
                <>
                  Follow-up 1: {formatDate(preview.fu1Date)} &middot; {time}{" "}
                  &middot; sent only to observers who haven&apos;t submitted
                  yet.
                </>
              )}
              {preview.fu1Date && preview.fu2Date && <br />}
              {preview.fu2Date && (
                <>
                  Follow-up 2 (final): {formatDate(preview.fu2Date)} &middot;{" "}
                  {time} &middot; sent only to observers still missing.
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

const DAY_OPTIONS = [
  { label: "1st of the month (default)", value: "1" },
  { label: "2nd of the month", value: "2" },
  { label: "3rd of the month", value: "3" },
  { label: "5th of the month", value: "5" },
  { label: "Last day of the previous month", value: "last" },
  { label: "Custom", value: "custom" },
];

const TIME_OPTIONS = [
  { label: "06:00", value: "06:00" },
  { label: "07:00", value: "07:00" },
  { label: "08:00", value: "08:00" },
  { label: "09:00", value: "09:00" },
  { label: "12:00", value: "12:00" },
  { label: "17:00", value: "17:00" },
];

const DEADLINE_OPTIONS = [
  { label: "3 days after reminder", value: "3" },
  { label: "5 days after reminder", value: "5" },
  { label: "7 days after reminder", value: "7" },
  { label: "10 days after reminder", value: "10" },
  { label: "No hard deadline", value: "none" },
];

const FOLLOWUP_OPTIONS_1 = [
  { label: "3 days after deadline", value: "3" },
  { label: "5 days after deadline", value: "5" },
  { label: "Off", value: "off" },
];

const FOLLOWUP_OPTIONS_2 = [
  { label: "7 days after deadline", value: "7" },
  { label: "10 days after deadline", value: "10" },
  { label: "Off", value: "off" },
];

const REGION_OVERRIDE_OPTIONS = [
  { label: "All regions use the default", value: "all" },
  { label: "Hhohho: override", value: "hhohho" },
  { label: "Manzini: override", value: "manzini" },
  { label: "Lubombo: override", value: "lubombo" },
  { label: "Shiselweni: override", value: "shiselweni" },
];

const ToggleGroup = ({ options, value, onChange }) => (
  <div className="flex gap-2">
    {options.map((opt) => (
      <button
        key={opt.value}
        type="button"
        className={`flex-1 py-2 px-3 border rounded-lg text-center cursor-pointer text-xs transition-all select-none ${
          value === opt.value
            ? "border-[#3E5EB9] bg-[#f0f4ff] text-[#333333] font-semibold"
            : "border-cardBorder bg-white text-[#606060]"
        }`}
        onClick={() => onChange(opt.value)}
      >
        {opt.label}
      </button>
    ))}
  </div>
);

const ReminderSchedulePage = () => {
  const [day, setDay] = useState("1");
  const [time, setTime] = useState("07:00");
  const [subjectTemplate, setSubjectTemplate] = useState(
    "Your {station} weather reading for {month} is due",
  );
  const [deadline, setDeadline] = useState("5");
  const [followUp1, setFollowUp1] = useState("3");
  const [followUp2, setFollowUp2] = useState("10");
  const [regionOverride, setRegionOverride] = useState("all");

  return (
    <div className="w-full h-auto">
      <PageHeader
        title="Reminder schedule"
        description="Configure when the automated monthly reminder goes out to every observer. Changes apply from next month onwards."
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
            {/* Section 1: Main monthly reminder */}
            <section className="border border-cardBorder bg-white">
              <div className="border-b border-cardBorder px-4 py-4 sm:px-6">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-[#3E5EB9] text-white text-xs font-bold flex items-center justify-center">
                    1
                  </span>
                  <h2 className="text-base font-semibold text-[#333333]">
                    Main monthly reminder
                  </h2>
                </div>
                <p className="text-xs text-[#606060] mt-1 ml-8">
                  Sent once a month to every active observer.
                </p>
              </div>
              <div className="p-4 sm:p-6 flex flex-col gap-5">
                <FieldGroup label="Day of the month">
                  <Select
                    style={{ width: "100%" }}
                    value={day}
                    onChange={setDay}
                    options={DAY_OPTIONS}
                  />
                </FieldGroup>

                <FieldGroup label="Time of day (SAST · UTC+2)">
                  <div className="grid grid-cols-2 gap-2.5">
                    <Select
                      style={{ width: "100%" }}
                      value={time}
                      onChange={setTime}
                      options={TIME_OPTIONS}
                    />
                    <Input
                      value="Local time — SAST (UTC+2)"
                      disabled
                      className="bg-[#f9fafb] italic"
                    />
                  </div>
                </FieldGroup>

                <FieldGroup
                  label="Subject line template"
                  hint="use {name}, {station}, {month}"
                >
                  <Input
                    value={subjectTemplate}
                    onChange={(e) => setSubjectTemplate(e.target.value)}
                  />
                </FieldGroup>

                <FieldGroup
                  label="Submission deadline"
                  hint="used in the email copy + as the nudge trigger"
                >
                  <Select
                    style={{ width: "100%" }}
                    value={deadline}
                    onChange={setDeadline}
                    options={DEADLINE_OPTIONS}
                  />
                </FieldGroup>
              </div>
            </section>

            {/* Section 2: Automatic follow-ups */}
            <section className="border border-cardBorder bg-white">
              <div className="border-b border-cardBorder px-4 py-4 sm:px-6">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-[#3E5EB9] text-white text-xs font-bold flex items-center justify-center">
                    2
                  </span>
                  <h2 className="text-base font-semibold text-[#333333]">
                    Automatic follow-ups
                  </h2>
                </div>
                <p className="text-xs text-[#606060] mt-1 ml-8">
                  Extra reminders sent if the observer hasn&apos;t submitted
                  yet.
                </p>
              </div>
              <div className="p-4 sm:p-6 flex flex-col gap-5">
                <FieldGroup label="First follow-up">
                  <ToggleGroup
                    options={FOLLOWUP_OPTIONS_1}
                    value={followUp1}
                    onChange={setFollowUp1}
                  />
                </FieldGroup>

                <FieldGroup label="Second follow-up (final)">
                  <ToggleGroup
                    options={FOLLOWUP_OPTIONS_2}
                    value={followUp2}
                    onChange={setFollowUp2}
                  />
                </FieldGroup>

                <FieldGroup label="After that">
                  <div className="border border-[#FAAD14] bg-[#f9f5eb] rounded-lg p-3.5 text-xs text-[#333333] leading-relaxed">
                    The observer is marked <b>at risk</b> in the admin dashboard
                    and their assigned admin is notified. From there, admins can
                    send an ad-hoc nudge or reassign the station.
                  </div>
                </FieldGroup>

                <div className="border-t border-cardBorder pt-5">
                  <FieldGroup label="Per-region overrides" hint="optional">
                    <p className="text-xs text-[#606060] mb-2.5">
                      Use this if a specific region needs a different day or
                      time (e.g. observers in Lubombo prefer earlier reminders
                      due to farm hours).
                    </p>
                    <div className="grid grid-cols-2 gap-2.5">
                      <Select
                        style={{ width: "100%" }}
                        value={regionOverride}
                        onChange={setRegionOverride}
                        options={REGION_OVERRIDE_OPTIONS}
                      />
                      <Button>+ Add override</Button>
                    </div>
                  </FieldGroup>
                </div>
              </div>
            </section>
          </div>

          {/* Next scheduled preview */}
          <NextReminderPreview
            day={day}
            time={time}
            deadline={deadline}
            followUp1={followUp1}
            followUp2={followUp2}
          />

          {/* Bottom actions */}
          <div className="flex flex-wrap items-center gap-3 py-4">
            <span className="text-xs text-[#606060] mr-auto">
              Schedule changes take effect from the next monthly cycle.
              Observers currently mid-cycle will finish under the previous
              schedule.
            </span>
            <Link href="/citizen-weather/admin">
              <Button>Cancel</Button>
            </Link>
            <Button type="primary">Save schedule</Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const FieldGroup = ({ label, hint, children }) => (
  <div>
    <label className="text-sm font-medium text-[#333333] block mb-1.5">
      {label}
      {hint && (
        <span className="text-xs text-[#606060] font-normal ml-1">
          &middot; {hint}
        </span>
      )}
    </label>
    {children}
  </div>
);

export default ReminderSchedulePage;
