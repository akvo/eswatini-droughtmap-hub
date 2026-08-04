"use client";

import { Button, Skeleton } from "antd";
import { CalendarOutlined, DownloadOutlined } from "@ant-design/icons";
import { DROUGHT_CATEGORY_COLOR } from "@/static/config";

const textOn = (hex = "#ffffff") => {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.6
    ? "#333333"
    : "#ffffff";
};

const HeroSection = ({ hero }) => {
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

  const catVal = status?.category ?? 0;
  const badgeBg = DROUGHT_CATEGORY_COLOR[catVal] || "#b9f8cf";
  const catLabel = catVal > 0 ? `D${catVal - 1}` : "Normal";

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
          className="text-base text-neutral-600 max-w-2xl leading-7 prose prose-neutral"
          dangerouslySetInnerHTML={{ __html: summary }}
        />

        <Button
          type="primary"
          icon={<DownloadOutlined />}
          size="large"
          className="mt-2 mb-32 print:hidden"
          onClick={() => {
            if (typeof window !== "undefined") {
              window.print();
            }
          }}
        >
          Download National Overview (PDF)
        </Button>
      </div>
    </section>
  );
};

export default HeroSection;
