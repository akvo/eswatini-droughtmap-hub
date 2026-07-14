import React, { useState } from "react";
import { Input, InputNumber, Button } from "antd";
import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import { api } from "@/lib/api";

export default function Step2Trigger({ formData, setFormData }) {
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const handlePreview = async () => {
    setPreviewLoading(true);
    try {
      const res = await api("POST", "/activities/trigger-preview", {
        triggers: formData.triggers,
      });
      setPreview(typeof res?.matched === "number" ? res : null);
    } catch {
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const dClasses = ["None", "D0", "D1", "D2", "D3", "D4"];

  // `target` routes the row into the trigger payload: "exp" rows become
  // triggers.exp[] conditions, "vuln" writes triggers.vuln = { op, value }.
  // All thresholds are whole numbers (litres, counts, hectares, IPC phase);
  // InputNumber precision={0} rejects decimals and commas at input time.
  const indicators = [
    {
      key: "water",
      target: "exp",
      label: "Water demand indicator",
      help: "Litres of water demand in the Inkhundla — whole number.",
      placeholder: "e.g. 2500",
      min: 0,
    },
    {
      key: "susceptibility",
      target: "vuln",
      label: "Susceptibility to drought threshold",
      help: "Vulnerability condition — IPC food-security phase, whole number from 1 to 4.",
      placeholder: "1-4",
      min: 1,
      max: 4,
    },
    {
      key: "cattle",
      target: "exp",
      label: "Cattle count",
      help: "Number of cattle exposed in the Inkhundla — whole number.",
      placeholder: "e.g. 1500",
      min: 0,
    },
    {
      key: "cropland",
      target: "exp",
      label: "Land use share",
      help: "Hectares of rain-fed cropland in the Inkhundla — whole number.",
      placeholder: "e.g. 3000",
      min: 0,
    },
    {
      key: "population",
      target: "exp",
      label: "Population",
      help: "Number of people exposed in the Inkhundla — whole number.",
      placeholder: "e.g. 10000",
      min: 0,
    },
  ];

  const handleDClassClick = (cls) => {
    const val = cls === "None" ? null : dClasses.indexOf(cls);
    setFormData({
      ...formData,
      triggers: {
        ...formData.triggers,
        dclass:
          val !== null
            ? { class: val, months: formData.triggers.dclass?.months || 1 }
            : null,
      },
    });
  };

  const handleMonthsChange = (val) => {
    if (!formData.triggers.dclass) return;
    setFormData({
      ...formData,
      triggers: {
        ...formData.triggers,
        dclass: { ...formData.triggers.dclass, months: val || 1 },
      },
    });
  };

  const handleIndicatorOpChange = (ind, op) => {
    if (ind.target === "vuln") {
      setFormData({
        ...formData,
        triggers: {
          ...formData.triggers,
          vuln: { op, value: formData.triggers.vuln?.value || 1 },
        },
      });
      return;
    }
    const existing = formData.triggers.exp.find((e) => e.indicator === ind.key);
    const newExp = existing
      ? formData.triggers.exp.map((e) =>
          e.indicator === ind.key ? { ...e, op } : e,
        )
      : [...formData.triggers.exp, { indicator: ind.key, op, value: 1 }];
    setFormData({
      ...formData,
      triggers: {
        ...formData.triggers,
        exp: newExp,
      },
    });
  };

  const handleIndicatorValChange = (ind, val) => {
    // InputNumber passes a number, or null when the input is cleared;
    // clearing removes the condition from the payload.
    if (ind.target === "vuln") {
      setFormData({
        ...formData,
        triggers: {
          ...formData.triggers,
          vuln:
            val === null
              ? null
              : { op: formData.triggers.vuln?.op || 1, value: val },
        },
      });
      return;
    }
    const existing = formData.triggers.exp.find((e) => e.indicator === ind.key);
    let newExp;
    if (val === null) {
      newExp = formData.triggers.exp.filter((e) => e.indicator !== ind.key);
    } else if (existing) {
      newExp = formData.triggers.exp.map((e) =>
        e.indicator === ind.key ? { ...e, value: val } : e,
      );
    } else {
      newExp = [
        ...formData.triggers.exp,
        { indicator: ind.key, op: 1, value: val },
      ];
    }
    setFormData({
      ...formData,
      triggers: {
        ...formData.triggers,
        exp: newExp,
      },
    });
  };

  const getDclassVal = () => {
    return formData.triggers.dclass?.class !== undefined
      ? dClasses[formData.triggers.dclass.class]
      : "None";
  };

  return (
    <div className="flex flex-col gap-6 w-full text-neutral-800">
      <div className="flex flex-col gap-2">
        <h4 className="text-xl font-medium text-[#333] m-0 leading-normal">
          Trigger condition
        </h4>
        <p className="text-base text-[#606060] m-0 leading-[24px]">
          Define the conditions that make this Response activity fire for an
          Inkhundla. The live preview below shows how many Tinkhundla it would
          fire for if activated against current data.
        </p>
      </div>
      <div className="h-px bg-[#e2e4e9] w-full" />

      {/* D-Class Threshold segmented pill */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-0.5 flex-1">
          <span className="text-sm text-[#606060] font-normal">
            D-class threshold:
          </span>
          <p className="text-xs text-[#909090] italic m-0 leading-[18px]">
            Validated drought class the Inkhundla must reach — None disables
            this condition.
          </p>
        </div>
        <div className="flex bg-[#eceff8] p-0.5 rounded-[10px] w-max border border-neutral-100">
          {dClasses.map((cls) => {
            const isActive = getDclassVal() === cls;
            // dClasses index matches DROUGHT_CATEGORY_VALUE (None=normal=0, D0=1, ...)
            const categoryColor = DROUGHT_CATEGORY_COLOR[dClasses.indexOf(cls)];
            const darkText = dClasses.indexOf(cls) < DROUGHT_CATEGORY_VALUE.d3;
            const activeStyle =
              cls === "None"
                ? { className: "bg-blue-600 text-white" }
                : {
                    className: darkText ? "text-neutral-800" : "text-white",
                    style: { backgroundColor: categoryColor },
                  };

            return (
              <button
                key={cls}
                type="button"
                onClick={() => handleDClassClick(cls)}
                style={isActive ? activeStyle.style : undefined}
                className={`px-3 py-1 rounded-[8px] text-sm font-normal transition-all ${
                  isActive
                    ? `${activeStyle.className} shadow-sm`
                    : "text-[#a4a4a4] hover:text-neutral-700 bg-transparent"
                }`}
              >
                {cls}
              </button>
            );
          })}
        </div>
      </div>

      {/* Months input */}
      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-col gap-0.5 flex-1 pb-2">
          <span className="text-sm text-[#606060] font-normal">
            for at least [N] consecutive months
          </span>
          <p className="text-xs text-[#909090] italic m-0 leading-[18px]">
            Whole number of months in a row the D-class must hold, e.g. D2 for
            at least 3 consecutive months.
          </p>
        </div>
        <div className="flex flex-col gap-1.5 w-[143px]">
          <span className="text-xs text-[#606060] font-normal">Amount</span>
          <InputNumber
            precision={0}
            min={1}
            placeholder="e.g. 3"
            value={formData.triggers.dclass?.months ?? null}
            onChange={handleMonthsChange}
            disabled={!formData.triggers.dclass}
            className="w-full h-10 border-[#d0d5dd] rounded-[4px] text-sm"
          />
        </div>
      </div>

      {/* Indicators Repeater List */}
      <div className="flex flex-col gap-4">
        {indicators.map((ind) => {
          const matched =
            ind.target === "vuln"
              ? formData.triggers.vuln
              : formData.triggers.exp.find((e) => e.indicator === ind.key);
          const currentOp = matched?.op || 1; // 1 = >=, 2 = <=
          const currentVal = matched?.value ?? null;

          return (
            <div
              key={ind.key}
              className="flex items-center justify-between gap-4"
            >
              <div className="flex flex-col gap-0.5 flex-1">
                <span className="text-sm text-[#606060] font-normal">
                  {ind.label}
                </span>
                <p className="text-xs text-[#909090] italic m-0 leading-[18px]">
                  {ind.help}
                </p>
              </div>

              {/* Operator Switch */}
              <div className="flex bg-[#eceff8] p-0.5 rounded-[10px] border border-neutral-100">
                <button
                  type="button"
                  onClick={() => handleIndicatorOpChange(ind, 1)}
                  className={`px-3 py-1 rounded-[8px] text-sm font-semibold transition-all ${
                    currentOp === 1
                      ? "bg-[#3e5eb9] text-white shadow-sm"
                      : "text-[#a4a4a4]"
                  }`}
                >
                  &ge;
                </button>
                <button
                  type="button"
                  onClick={() => handleIndicatorOpChange(ind, 2)}
                  className={`px-3 py-1 rounded-[8px] text-sm font-semibold transition-all ${
                    currentOp === 2
                      ? "bg-[#3e5eb9] text-white shadow-sm"
                      : "text-[#a4a4a4]"
                  }`}
                >
                  &le;
                </button>
              </div>

              {/* Value Input */}
              <div className="w-[143px]">
                <InputNumber
                  precision={0}
                  min={ind.min}
                  max={ind.max}
                  placeholder={ind.placeholder}
                  value={currentVal}
                  onChange={(val) => handleIndicatorValChange(ind, val)}
                  className="w-full h-10 border-[#d0d5dd] rounded-[4px] text-sm"
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Other condition (free-form) */}
      <div className="flex flex-col gap-2 w-full">
        <div className="flex flex-col gap-0.5">
          <label className="text-sm text-[#606060] font-normal">
            Other condition (free-form)
          </label>
          <p className="text-xs text-[#909090] italic m-0 leading-[18px]">
            Free-form note for reviewers — not evaluated automatically.
          </p>
        </div>
        <Input.TextArea
          placeholder="e.g. high IKS drought signal AND IKS valid this period"
          value={formData.triggers.other || ""}
          onChange={(e) =>
            setFormData({
              ...formData,
              triggers: {
                ...formData.triggers,
                other: e.target.value || null,
              },
            })
          }
          rows={4}
          className="w-full border-[#d2d2d2] rounded-[8px] p-3 text-sm focus:border-blue-500"
        />
      </div>

      {/* Live Preview alert banner */}
      <div className="bg-[#eceff8] text-[#333] rounded-[8px] px-3.5 py-2.5 text-sm flex items-center gap-2 font-medium w-full">
        <span className="text-[#3e5eb9] text-base">&#9888;</span>
        <span className="flex-1">
          {preview
            ? `Would fire for ${preview.matched} of ${preview.total} Tinkhundla`
            : "Preview how many Tinkhundla this trigger would fire for"}
        </span>
        <Button size="small" loading={previewLoading} onClick={handlePreview}>
          Preview
        </Button>
      </div>
    </div>
  );
}
