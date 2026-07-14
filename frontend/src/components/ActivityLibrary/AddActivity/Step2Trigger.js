import React from "react";
import { Input, Button } from "antd";

export default function Step2Trigger({ formData, setFormData }) {
  const dClasses = ["None", "D0", "D1", "D2", "D3", "D4"];

  const indicators = [
    { key: "water", label: "Water demand indicator" },
    { key: "susceptibility", label: "Susceptibility to drought threshold" },
    { key: "cattle", label: "Cattle count" },
    { key: "land_use", label: "Land use share" },
    { key: "population", label: "Population" },
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
    const months = parseInt(val) || 1;
    if (formData.triggers.dclass) {
      setFormData({
        ...formData,
        triggers: {
          ...formData.triggers,
          dclass: { ...formData.triggers.dclass, months },
        },
      });
    }
  };

  const handleIndicatorOpChange = (key, op) => {
    const existing = formData.triggers.exp.find((e) => e.indicator === key);
    let newExp = [...formData.triggers.exp];
    if (existing) {
      existing.op = op;
    } else {
      newExp.push({ indicator: key, op, value: 0.75 });
    }
    setFormData({
      ...formData,
      triggers: {
        ...formData.triggers,
        exp: newExp,
      },
    });
  };

  const handleIndicatorValChange = (key, val) => {
    const numVal = parseFloat(val) || 0;
    const existing = formData.triggers.exp.find((e) => e.indicator === key);
    let newExp = [...formData.triggers.exp];
    if (existing) {
      existing.value = numVal;
    } else {
      newExp.push({ indicator: key, op: 1, value: numVal });
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
        <span className="text-sm text-[#606060] font-normal">
          D-class threshold:
        </span>
        <div className="flex bg-[#eceff8] p-0.5 rounded-[10px] w-max border border-neutral-100">
          {dClasses.map((cls) => {
            const isActive = getDclassVal() === cls;
            let activeBg = "bg-blue-600 text-white";
            if (cls === "D3") activeBg = "bg-[#c23f01] text-white";
            if (cls === "D4") activeBg = "bg-[#b10d0b] text-white";

            return (
              <button
                key={cls}
                type="button"
                onClick={() => handleDClassClick(cls)}
                className={`px-3 py-1 rounded-[8px] text-sm font-normal transition-all ${
                  isActive
                    ? `${activeBg} shadow-sm`
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
        <span className="text-sm text-[#606060] font-normal pb-2">
          for at least [N] consecutive months
        </span>
        <div className="flex flex-col gap-1.5 w-[143px]">
          <span className="text-xs text-[#606060] font-normal">Amount</span>
          <Input
            type="number"
            placeholder="0,75"
            value={formData.triggers.dclass?.months || ""}
            onChange={(e) => handleMonthsChange(e.target.value)}
            disabled={!formData.triggers.dclass}
            className="w-full h-10 border-[#d0d5dd] rounded-[4px] px-3 text-sm"
          />
        </div>
      </div>

      {/* Indicators Repeater List */}
      <div className="flex flex-col gap-4">
        {indicators.map((ind) => {
          const matched = formData.triggers.exp.find(
            (e) => e.indicator === ind.key,
          );
          const currentOp = matched?.op || 1; // 1 = >=, 2 = <=
          const currentVal = matched?.value !== undefined ? matched.value : "";

          return (
            <div
              key={ind.key}
              className="flex items-center justify-between gap-4"
            >
              <span className="text-sm text-[#606060] font-normal flex-1">
                {ind.label}
              </span>

              {/* Operator Switch */}
              <div className="flex bg-[#eceff8] p-0.5 rounded-[10px] border border-neutral-100">
                <button
                  type="button"
                  onClick={() => handleIndicatorOpChange(ind.key, 1)}
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
                  onClick={() => handleIndicatorOpChange(ind.key, 2)}
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
                <Input
                  type="number"
                  placeholder="0,75"
                  value={currentVal}
                  onChange={(e) =>
                    handleIndicatorValChange(ind.key, e.target.value)
                  }
                  className="w-full h-10 border-[#d0d5dd] rounded-[4px] px-3 text-sm"
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Other condition (free-form) */}
      <div className="flex flex-col gap-2 w-full">
        <label className="text-sm text-[#606060] font-normal">
          Other condition (free-form)
        </label>
        <Input.TextArea
          placeholder="Add reviewer notes..."
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

      {/* Live Preview static alert banner */}
      <div className="bg-[#eceff8] text-[#333] rounded-[8px] px-3.5 py-2.5 text-sm flex items-center gap-2 font-medium w-full">
        <span className="text-[#3e5eb9] text-base">&#9888;</span> Would fire for
        N of 59 Tinkhundla
      </div>
    </div>
  );
}
