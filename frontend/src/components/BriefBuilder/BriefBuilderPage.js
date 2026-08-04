"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Button, Spin, Tooltip } from "antd";
import { HomeOutlined } from "@ant-design/icons";
import FeedbackSection from "@/components/FeedbackSection";
import { useBrief } from "@/context/BriefContextProvider";
import useBriefData from "@/hooks/useBriefData";
import BriefComponentPanel from "./BriefComponentPanel";
import ForwardBriefSlideIn from "./ForwardBriefSlideIn";

// The preview pulls in akvo-charts (ECharts touches `window` at import) and
// tinymce, neither of which survives the prerender. Deferred client-side, the
// same way the Detailed insights tabs load their charts.
const BriefPreview = dynamic(() => import("./BriefPreview"), {
  ssr: false,
  loading: () => (
    <div className="flex min-h-[480px] items-center justify-center">
      <Spin size="large" />
    </div>
  ),
});

/**
 * Brief Builder shell (Figma 4159:191051 empty / 4155:169634 selected).
 *
 * Two columns: the 420px selection panel and the 852px live preview. Below
 * lg they stack preview-first — a phone user is reading a brief, not building
 * one.
 */
const BriefBuilderPage = () => {
  const {
    applied,
    administrationId,
    selectedInkhundla,
    isTwgMember,
    twgLoading,
  } = useBrief();
  const [forwardOpen, setForwardOpen] = useState(false);

  // Fetched here rather than inside BriefPreview so the forward slide-in can
  // name the cycle without firing the same three requests a second time.
  const briefData = useBriefData(administrationId);
  const period =
    briefData.cdi?.value?.period ??
    briefData.cdi?.data?.[0]?.meta?.period ??
    null;

  // Nothing to export until there is a brief to export.
  const hasBrief = Boolean(applied.inkhundla && applied.components.length);
  // Fails closed: disabled while /users/me is still in flight, so the gate
  // never flickers open for a user without a TWG (design doc D-5).
  const canForward = hasBrief && !twgLoading && isTwgMember;

  const forwardHint = !hasBrief
    ? "Select an Inkhundla and at least one component first."
    : twgLoading
      ? "Checking your Technical Working Group membership..."
      : !isTwgMember
        ? "Only TWG members can forward briefs. Ask an administrator to assign your Technical Working Group."
        : "";

  return (
    // -mt-3 cancels AppShell's pt-3: the shell wraps every page in a white
    // container with 12px of top padding, which otherwise shows as a white
    // strip above this full-bleed tinted band. PageHeader does the same.
    <div className="relative left-1/2 -mt-3 w-screen -translate-x-1/2 bg-brandTint py-8">
      <div className="mx-auto w-full max-w-[1280px] px-4">
        {/* Breadcrumb bar is its own card (Figma 4155:179244): white, hairline
            border, 76px. -mb-px collapses its bottom border into the top of
            the panel/preview row below, as the design has them overlapping by
            1px rather than gapped. */}
        <div className="-mb-px flex h-[76px] items-center gap-4 border border-cardBorder bg-white p-4">
          <nav className="flex flex-1 items-center gap-2 text-sm">
            <Link
              href="/"
              aria-label="Home"
              className="flex items-center text-neutral-500 transition-colors hover:text-primary"
            >
              <HomeOutlined />
            </Link>
            {/* A vertical rule, not a "/" — the design's separator. */}
            <span aria-hidden className="h-4 w-px bg-cardBorder" />
            <span className="leading-4 tracking-[-0.25px] text-primary">
              Brief builder
            </span>
          </nav>
        </div>

        <div className="flex flex-col gap-2 lg:flex-row lg:items-start">
          {/* Preview first in the DOM so a narrow viewport reads the brief
              before the 11-checkbox panel; lg:order restores the design. */}
          <div className="order-1 min-w-0 flex-1 border border-cardBorder bg-white lg:order-2">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cardBorder px-4 py-4">
              <h2 className="mb-0 text-[20px] font-bold leading-[30px] text-neutral-800">
                Live preview
              </h2>
              <div className="flex items-center gap-2">
                <Tooltip title={forwardHint}>
                  <span>
                    <Button
                      disabled={!canForward}
                      onClick={() => setForwardOpen(true)}
                    >
                      Forward to
                    </Button>
                  </span>
                </Tooltip>
                <Tooltip title="PDF export is not available yet — it ships with the backend round.">
                  <span>
                    {/* Renders per the design and does nothing on purpose
                        (design doc D-2). TODO(BB-2): wire once the export
                        approach is chosen. */}
                    <Button type="primary" disabled={!hasBrief}>
                      Download PDF
                    </Button>
                  </span>
                </Tooltip>
              </div>
            </div>
            <BriefPreview data={briefData} />
          </div>

          <div className="order-2 lg:order-1">
            <BriefComponentPanel />
          </div>
        </div>

        <div className="mt-6 [&>div]:mt-0">
          <FeedbackSection />
        </div>
      </div>

      <ForwardBriefSlideIn
        visible={forwardOpen}
        onClose={() => setForwardOpen(false)}
        inkhundla={selectedInkhundla}
        period={period}
        components={applied.components}
      />
    </div>
  );
};

export default BriefBuilderPage;
