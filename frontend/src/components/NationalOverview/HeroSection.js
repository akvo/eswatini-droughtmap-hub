"use client";

import { useCallback, useState } from "react";
import { Button, Skeleton, Tooltip, message } from "antd";
import { CalendarOutlined, DownloadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { usePrintContext } from "@/context/PrintContextProvider";
import {
  DROUGHT_CATEGORY_VALUE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_CODE,
  OVERVIEW_NARRATIVE_MAX_CHARS,
} from "@/static/config";
import { textOn } from "@/lib/helper";

const HeroSection = ({ hero }) => {
  const [downloading, setDownloading] = useState(false);
  const { expandForPrint, collapse } = usePrintContext() ?? {};

  // Browser print, not a generated file (D-1): the user confirms a "Save as
  // PDF" dialog. document.title is the only lever a page has over the
  // suggested filename, and every target browser seeds it from there.
  const handleDownload = useCallback(async () => {
    // `period` is the CDI month the overview describes, not today and not the
    // map selector's current month (D-6). Pattern-checked before it reaches
    // document.title so a malformed value cannot smuggle in path separators.
    const period = /^\d{4}-\d{2}$/.test(hero?.period ?? "")
      ? hero.period
      : dayjs().format("YYYY-MM");

    const prevTitle = document.title;
    const restore = () => {
      document.title = prevTitle;
      // Dropping the class resizes the maps back, which the same
      // ResizeObserver uses as its cue to restore the user's view (D-10).
      document.documentElement.classList.remove("printing");
      collapse?.();
      setDownloading(false);
    };

    setDownloading(true);
    document.title = `National_Drought_overview_${period}.pdf`;
    // Apply the print geometry NOW, while the page is still on screen and
    // JavaScript can still run. Leaflet has to re-fit its bounds after the
    // container changes size, and there is no moment during a synchronous
    // window.print() at which that can happen — so the resize has to come
    // first. (D-10)
    document.documentElement.classList.add("printing");
    // Fires on cancel as well as completion, so the title, the expanded print
    // content and the button all recover if the user backs out of the dialog.
    window.addEventListener("afterprint", restore, { once: true });

    try {
      // Ask every section to render its print-only content and wait for the
      // six map-layer fetches behind it (D-9). This is the real work the
      // spinner covers — unlike the old frame-deferral, it genuinely takes
      // longer than a moment.
      await expandForPrint?.();
      // One more frame so the newly mounted Leaflet instances finish laying
      // out — and, since the `printing` class above has already resized them,
      // so their re-fit has landed — before the snapshot (D-5, D-10).
      await new Promise((resolve) => requestAnimationFrame(resolve));
      window.print();
    } catch (err) {
      console.error("PDF export failed:", err);
      window.removeEventListener("afterprint", restore);
      restore();
      message.error("Failed to download PDF. Please try again.");
    }
  }, [hero, expandForPrint, collapse]);

  if (!hero) {
    return (
      <section className="relative w-full flex flex-col items-center text-center py-12 gap-6 min-h-[300px]">
        <Skeleton.Button active size="small" style={{ width: 160 }} />
        <Skeleton.Input active size="large" style={{ width: 340 }} />
        <Skeleton.Node active style={{ width: 480, height: 70 }} />
      </section>
    );
  }

  const {
    status = { category: 0, label: "Normal / No Drought" },
    published = "-",
    nextUpdate = "-",
    headline = "Drought Situation Overview",
    summary = "",
  } = hero;

  const catVal = status?.category;
  const badgeBg =
    DROUGHT_CATEGORY_COLOR?.[catVal] ||
    DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.none];
  const catLabel =
    DROUGHT_CATEGORY_CODE?.[catVal] ||
    DROUGHT_CATEGORY_CODE[DROUGHT_CATEGORY_VALUE.none];

  return (
    <section className="relative w-full flex flex-col items-center text-center py-12 gap-6">
      <div
        aria-hidden
        className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
      />
      <div className="relative flex flex-col items-center gap-6">
        <div className="flex items-center gap-4">
          <span
            className="inline-block rounded px-2.5 py-1 text-xs font-semibold"
            style={{ backgroundColor: badgeBg, color: textOn(badgeBg) }}
          >
            National Status: {catLabel}
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-neutral-500">
          <span className="flex items-center gap-1.5">
            <CalendarOutlined /> Published:{" "}
            <strong className="text-neutral-700">{published}</strong>
          </span>
          <span className="flex items-center gap-1.5">
            <CalendarOutlined /> Next update:{" "}
            <strong className="text-neutral-700">{nextUpdate}</strong>
          </span>
        </div>

        <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold text-neutral-800 max-w-2xl leading-tight">
          {headline}
        </h1>

        <div
          className="text-base text-neutral-600 w-full max-w-3xl leading-7 prose prose-neutral"
          dangerouslySetInnerHTML={{
            __html: summary.slice(0, OVERVIEW_NARRATIVE_MAX_CHARS),
          }}
        />

        <Tooltip title="Download full page as PDF">
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            size="large"
            className="mt-2 mb-32 print:hidden"
            loading={downloading}
            onClick={handleDownload}
          >
            Download National Overview (PDF)
          </Button>
        </Tooltip>
      </div>
    </section>
  );
};

export default HeroSection;
