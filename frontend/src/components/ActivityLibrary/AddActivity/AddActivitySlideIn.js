import React, { useState } from "react";
import { Button, message } from "antd";
import { api } from "@/lib/api";
import { useUserContext } from "@/context/UserContextProvider";
import { USER_ROLES, ACTIVITY_STATUS } from "@/static/config";
import Step1Identify from "./Step1Identify";
import Step2Trigger from "./Step2Trigger";
import Step3Ownership from "./Step3Ownership";
import Step4Signoff from "./Step4Signoff";
import Can from "@/components/Can";

export default function AddActivitySlideIn({ visible, onClose, onSuccess }) {
  const userContext = useUserContext();
  const [currentStep, setCurrentStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  const [formData, setFormData] = useState({
    sector: null,
    protocol_id: "",
    title: "",
    description: "",
    triggers: {
      dclass: null,
      vuln: null,
      exp: [],
      other: null,
    },
    owner: "",
    coord_with: "",
    response_type: null,
    source_doc: "",
    source_file: null,
    notes: "",
  });

  if (!visible) return null;

  const steps = [
    { number: 1, label: "Identify", desc: "Step 1" },
    { number: 2, label: "Trigger", desc: "Step 2" },
    { number: 3, label: "Ownership", desc: "Step 3" },
    { number: 4, label: "Sign-off", desc: "Step 4" },
  ];

  const handleNext = () => {
    if (currentStep === 1) {
      const step1Errors = {};
      if (!formData.sector) step1Errors.sector = "Sector is required.";
      if (!formData.title?.trim()) step1Errors.title = "Title is required.";

      if (Object.keys(step1Errors).length > 0) {
        setErrors(step1Errors);
        return;
      }
      setErrors({});
    }
    setCurrentStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setCurrentStep((prev) => prev - 1);
  };

  const handleSaveAsDraft = async () => {
    await submitForm(ACTIVITY_STATUS.draft);
  };

  const handlePublish = async () => {
    await submitForm(ACTIVITY_STATUS.active);
  };

  const submitForm = async (statusVal) => {
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("sector", formData.sector || "");
      fd.append("title", formData.title || "");
      fd.append("status", statusVal);

      if (formData.description) fd.append("description", formData.description);

      // Map exposure indicators to backend-approved EXPOSURE_INDICATORS
      const mappedExp = [];
      if (formData.triggers?.exp) {
        formData.triggers.exp.forEach((expCond) => {
          let indicator = expCond.indicator;
          if (indicator === "land_use") {
            indicator = "cropland";
          }
          // Only append valid backend exposure indicators
          if (
            ["population", "cropland", "water", "cattle"].includes(indicator)
          ) {
            mappedExp.push({
              indicator,
              op: expCond.op,
              value: expCond.value,
            });
          }
        });
      }

      // Serialize triggers to JSON string
      const triggerEnvelope = {
        dclass: formData.triggers?.dclass || null,
        vuln: formData.triggers?.vuln || null,
        exp: mappedExp,
        other: formData.triggers?.other || null,
      };
      fd.append("triggers", JSON.stringify(triggerEnvelope));

      if (formData.owner) fd.append("owner", formData.owner);
      if (formData.coord_with) fd.append("coord_with", formData.coord_with);
      if (formData.response_type)
        fd.append("response_type", formData.response_type);
      if (formData.source_doc) fd.append("source_doc", formData.source_doc);
      if (formData.source_file) fd.append("source_file", formData.source_file);

      // Call API
      const res = await api("POST", "/activities", fd);
      if (res && res.id) {
        let warningSubtitle = "";
        // If status is Publish (2), call transition API to transition draft to active
        if (statusVal === ACTIVITY_STATUS.active) {
          try {
            await api("POST", `/activity/${res.id}/transition`, {
              to_status: ACTIVITY_STATUS.active,
            });
          } catch (transErr) {
            console.warn(
              "Could not transition activity automatically:",
              transErr,
            );
            // Non-blocking warning: pass subtitle message to modal
            warningSubtitle =
              "Activity created as Draft. Only Admins can publish directly.";
          }
        }

        // Reset state
        setCurrentStep(1);
        setFormData({
          sector: null,
          protocol_id: "",
          title: "",
          description: "",
          triggers: {
            dclass: null,
            vuln: null,
            exp: [],
            other: null,
          },
          owner: "",
          coord_with: "",
          response_type: null,
          source_doc: "",
          source_file: null,
          notes: "",
        });
        setErrors({});
        onSuccess(warningSubtitle);
      } else {
        // Fallback for API error messages
        const errMsg = res?.message || "Failed to submit response activity";
        message.error(errMsg);
      }
    } catch (err) {
      console.error(err);
      if (err?.message) {
        // Try parsing JSON error response if possible
        try {
          const detail = JSON.parse(
            err.message.substring(err.message.indexOf("{")),
          );
          if (detail) {
            const firstErrKey = Object.keys(detail)[0];
            const firstErrVal = detail[firstErrKey];
            message.error(
              `${firstErrKey}: ${Array.isArray(firstErrVal) ? firstErrVal[0] : firstErrVal}`,
            );
            return;
          }
        } catch (_) {}
        message.error(err.message);
      } else {
        message.error(
          "Failed to submit response activity due to a network or validation error",
        );
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />

      {/* Slide-in Container */}
      <div className="relative w-[604px] h-screen bg-white flex flex-col shadow-2xl z-10 border-l border-neutral-300">
        {/* Sticky Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-neutral-200 sticky top-0 bg-white z-10">
          <span className="text-base font-semibold text-neutral-800">
            Add new response activity
          </span>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-700 text-lg font-semibold"
          >
            &times;
          </button>
        </div>

        {/* Form Body Area */}
        <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-6">
          {/* Progress Indicator Stepper */}
          <div className="flex justify-between items-center w-full px-2 mb-2">
            {steps.map((st, i) => {
              const isActive = currentStep === st.number;
              const isCompleted = currentStep > st.number;
              return (
                <React.Fragment key={st.number}>
                  {i > 0 && (
                    <div
                      className={`flex-1 h-0.5 mx-2 ${isCompleted ? "bg-blue-600" : "bg-neutral-200"}`}
                    />
                  )}
                  <div className="flex flex-col items-center gap-1.5 relative">
                    <div
                      className={`size-5 rounded-full flex items-center justify-center text-xs font-semibold ${
                        isCompleted
                          ? "bg-blue-600 text-white"
                          : isActive
                            ? "border-2 border-blue-600 text-blue-600 bg-white"
                            : "bg-neutral-100 text-neutral-400"
                      }`}
                    >
                      {isCompleted ? "✓" : st.number}
                    </div>
                    <span
                      className={`text-xs font-medium ${isActive ? "text-blue-600 font-bold" : "text-neutral-500"}`}
                    >
                      {st.label}
                    </span>
                  </div>
                </React.Fragment>
              );
            })}
          </div>

          {/* Active Step Content */}
          <div className="flex-1">
            {currentStep === 1 && (
              <Step1Identify
                formData={formData}
                setFormData={setFormData}
                errors={errors}
                userContext={userContext}
              />
            )}
            {currentStep === 2 && (
              <Step2Trigger formData={formData} setFormData={setFormData} />
            )}
            {currentStep === 3 && (
              <Step3Ownership formData={formData} setFormData={setFormData} />
            )}
            {currentStep === 4 && (
              <Step4Signoff formData={formData} setFormData={setFormData} />
            )}
          </div>
        </div>

        {/* Sticky Footer */}
        <div className="px-6 py-4 border-t border-neutral-200 flex justify-between items-center sticky bottom-0 bg-white z-10 w-full">
          <Button
            type="link"
            onClick={handleSaveAsDraft}
            loading={submitting}
            className="text-blue-800 font-semibold p-0"
          >
            Save as draft
          </Button>

          <div className="flex items-center gap-3">
            {currentStep > 1 ? (
              <Button onClick={handleBack} disabled={submitting}>
                Back
              </Button>
            ) : (
              <Button onClick={onClose} disabled={submitting}>
                Cancel
              </Button>
            )}

            {currentStep < 4 ? (
              <Button
                type="primary"
                onClick={handleNext}
                className="bg-blue-600 border-blue-600"
              >
                Next
              </Button>
            ) : (
              <>
                <Can I="update" a="Activity">
                  <Button
                    type="primary"
                    onClick={handlePublish}
                    loading={submitting}
                    className="bg-blue-600 border-blue-600"
                  >
                    Publish
                  </Button>
                </Can>
                {userContext?.role !== "admin" &&
                  userContext?.role !== USER_ROLES.admin && (
                    <Button
                      type="primary"
                      onClick={handlePublish}
                      loading={submitting}
                      className="bg-blue-600 border-blue-600"
                    >
                      Submit for Review
                    </Button>
                  )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
