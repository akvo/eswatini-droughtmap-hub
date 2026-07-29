"use client";

import { useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { InputNumber, Input, Button, message } from "antd";
import {
  CalendarOutlined,
  FormOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import CWHeader from "@/components/CitizenWeather/CWHeader";
import { Thermometer, Droplet } from "@/components/CitizenWeather/CWIcons";
import {
  observerProfile,
  currentReading,
} from "@/static/mocks/citizen-weather";

const { TextArea } = Input;

const FIELDS = [
  {
    key: "temp_min",
    label: "Monthly minimum temperature",
    unit: "\u00B0C",
    icon: <Thermometer size={18} />,
    iconClass: "tmin",
    placeholder: "e.g. 11.4",
    hint: "The lowest temperature reading you recorded this month.",
  },
  {
    key: "temp_max",
    label: "Monthly maximum temperature",
    unit: "\u00B0C",
    icon: <Thermometer size={18} />,
    iconClass: "tmax",
    placeholder: "e.g. 29.6",
    hint: "The highest temperature reading you recorded this month.",
  },
  {
    key: "rainfall",
    label: "Total rainfall for the month",
    unit: "mm",
    icon: <Droplet size={18} />,
    iconClass: "rain",
    placeholder: "e.g. 42",
    hint: "The total rain your gauge measured across the month.",
  },
  {
    key: "soil_moisture",
    label: "Average soil moisture",
    unit: "% or m\u00B3/m\u00B3",
    icon: <Droplet size={18} />,
    iconClass: "smoist",
    placeholder: "e.g. 0.21",
    hint: "Skip if your station doesn't have a soil moisture probe.",
  },
  {
    key: "soil_temp",
    label: "Average soil temperature",
    unit: "\u00B0C",
    icon: <Thermometer size={18} />,
    iconClass: "stemp",
    placeholder: "e.g. 18.7",
    hint: "Skip if your station doesn't have a soil temperature probe.",
  },
];

const PeriodFormPage = () => {
  const params = useParams();
  const router = useRouter();
  const period = params.period;

  const periodLabel = useMemo(() => {
    if (!period) return "";
    const [year, month] = period.split("-");
    const monthNames = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December",
    ];
    const monthIndex = parseInt(month, 10) - 1;
    return `${monthNames[monthIndex] || month} ${year}`;
  }, [period]);

  const [values, setValues] = useState({
    temp_min: currentReading.values.temp_min,
    temp_max: currentReading.values.temp_max,
    rainfall: currentReading.values.rainfall,
    soil_moisture: currentReading.values.soil_moisture,
    soil_temp: currentReading.values.soil_temp,
  });
  const [notes, setNotes] = useState(currentReading.notes || "");

  const filledCount = useMemo(
    () => FIELDS.filter((f) => values[f.key] != null).length,
    [values]
  );

  const totalFields = FIELDS.length;
  const progressPct = (filledCount / totalFields) * 100;

  return (
    <div className="w-full h-auto">
      {/* Header */}
      <div className="px-4 sm:px-8 md:px-12 xl:px-20 pt-4 pb-0">
        <div className="mx-auto w-full max-w-[1280px]">
          <CWHeader
            subtitle={`Your station \u00B7 ${observerProfile.station.shortName} \u00B7 ${observerProfile.station.region} region`}
            userName={observerProfile.name}
            userInitials={observerProfile.initials}
          />
        </div>
      </div>

      {/* Hero — full width with pattern */}
      <section className="relative overflow-hidden bg-white px-4 pb-24 pt-10 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
        />
        <div className="relative mx-auto w-full max-w-[1280px]">
          <div className="flex items-center gap-2 mb-3">
            <span className="rounded border border-[#d2d2d2] px-2.5 py-1 text-sm text-[#333333] font-semibold inline-flex items-center gap-1.5">
              <CalendarOutlined /> {periodLabel}
            </span>
          </div>
          <h1 className="text-[28px] font-bold leading-10 text-[#333333] mb-2">
            Sanibonani {observerProfile.name.split(" ")[0]} &mdash; let&apos;s log{" "}
            {periodLabel.split(" ")[0]}&apos;s weather.
          </h1>
          <p className="text-sm leading-6 text-[#606060] mb-4">
            Fill in whatever your station recorded. You can skip any field you
            don&apos;t have a value for.
          </p>
          <div className="flex items-center gap-3">
            <div className="h-2 flex-1 max-w-[300px] rounded-full bg-[#eaecf0] overflow-hidden">
              <div
                className="h-full rounded-full bg-[#3E5EB9] transition-all"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <span className="text-sm text-[#606060]">
              {filledCount} of {totalFields} fields filled
            </span>
          </div>
        </div>
      </section>

      {/* Form — full width with brandTint background */}
      <div className="relative px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <div className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px]">
          {/* Field cards */}
          <section className="border border-[#eaecf0] bg-white mb-4">
            <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6">
              <h2 className="text-xl font-semibold leading-7 text-[#333333]">
                Weather readings
              </h2>
            </div>
            <div className="p-4 sm:p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {FIELDS.map((field) => (
                  <div
                    key={field.key}
                    className="border border-[#eaecf0] rounded-lg p-4"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <div className={`field-icon ${field.iconClass}`}>
                        {field.icon}
                      </div>
                      <span className="text-sm font-semibold text-[#333333] flex-1">
                        {field.label}
                      </span>
                      <span className="text-xs text-[#606060]">{field.unit}</span>
                    </div>
                    <InputNumber
                      style={{ width: "100%" }}
                      placeholder={field.placeholder}
                      value={values[field.key]}
                      onChange={(v) => setValues({ ...values, [field.key]: v })}
                      controls={false}
                    />
                    <div className="text-xs text-[#606060] mt-2">{field.hint}</div>
                  </div>
                ))}

                {/* Reassurance card */}
                <div className="border border-[#eaecf0] rounded-lg p-4 flex flex-col justify-center">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircleOutlined style={{ color: "#12b76a", fontSize: 18 }} />
                    <span className="text-sm font-semibold text-[#606060]">
                      All fields are optional
                    </span>
                  </div>
                  <div className="text-xs text-[#606060] leading-relaxed">
                    You don&apos;t have to fill every field. Share what you recorded,
                    leave the rest blank, and add a note if something was unusual or if a
                    gauge stopped working.
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Notes */}
          <section className="border border-[#eaecf0] bg-white mb-4">
            <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6">
              <div className="flex items-center gap-2">
                <FormOutlined style={{ color: "#606060" }} />
                <h2 className="text-base font-semibold leading-7 text-[#333333]">
                  Anything else worth telling us? (optional)
                </h2>
              </div>
            </div>
            <div className="p-4 sm:p-6">
              <TextArea
                rows={3}
                placeholder="Broken sensor? Unusual event? A quick observation from around your Inkhundla? Write it here."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </section>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 py-4">
            <span className="text-sm text-[#606060] mr-auto">
              You can save what you have and come back later, or submit now.
            </span>
            <Button onClick={() => message.info("Draft saved.")}>
              Save draft
            </Button>
            <Button
              type="primary"
              onClick={() => {
                message.success("Reading submitted. Siyabonga!");
                router.push("/citizen-weather/observe");
              }}
            >
              Submit {periodLabel} reading
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PeriodFormPage;
