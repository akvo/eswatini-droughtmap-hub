import Link from "next/link";
import { Button, Skeleton } from "antd";
import { CalendarOutlined } from "@ant-design/icons";
import { SECTOR_CARD_ICONS } from "@/static/config";

const Stat = ({ value, label }) => (
  <div className="flex-1 flex flex-col gap-0.5">
    <span className="text-sm leading-[21px] text-primary">{value}</span>
    <span className="text-xs leading-[18px] text-[#5b616d]">{label}</span>
  </div>
);

const SectorCard = ({ sector }) => (
  <div className="p-4 flex flex-col gap-6">
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <span className="shrink-0 flex items-center size-6 [&>img]:!size-6">
          {SECTOR_CARD_ICONS[sector.id]}
        </span>
        <h4 className="flex-1 text-base leading-6 text-[#11142d]">
          {sector.label}
        </h4>
      </div>
      <div className="flex gap-3">
        <Stat value={sector.activities} label="Activities" />
        <Stat value={sector.tinkhundla} label="Tinkhundla" />
      </div>
    </div>
    <div className="flex flex-col gap-4">
      <hr className="border-t border-cardBorder" />
      <p className="text-xs leading-[18px] text-textSecondary">
        {sector.description}
      </p>
    </div>
  </div>
);

const ResponseActivities = ({ responseActivities }) => {
  if (!responseActivities) {
    return (
      <section className="w-full">
        <div className="border border-neutral-200 bg-white p-4 min-h-[240px] flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
            <Skeleton.Input active size="small" style={{ width: 200 }} />
            <Skeleton.Input active size="small" style={{ width: 140 }} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
            <Skeleton.Node active style={{ width: "100%", height: 90 }} />
            <Skeleton.Node active style={{ width: "100%", height: 90 }} />
          </div>
        </div>
      </section>
    );
  }
  const {
    lastUpdated = "-",
    summary = "No active response activities recorded.",
    sectors = [],
  } = responseActivities || {};

  return (
    <section className="w-full">
      <div className="border border-cardBorder bg-white">
        {/* Header + Summary */}
        <div className="flex flex-col gap-1 p-4">
          <div className="flex items-center gap-4">
            <h2 className="flex-1 text-xl leading-[30px] font-medium text-textBody">
              Response Activities
            </h2>
            <span className="shrink-0 flex items-center gap-2">
              <span className="flex items-center gap-1.5 text-sm leading-[21px] text-textSecondary">
                <CalendarOutlined /> last updated:
              </span>
              <span className="rounded border border-cardBorder px-2 py-0.5 text-sm leading-[21px] text-textBody">
                {lastUpdated}
              </span>
            </span>
          </div>
          <p className="text-sm leading-[21px] text-textSecondary">{summary}</p>
        </div>

        {/* Sector cards — 2x2 grid. ponytail: gap-px over a cardBorder backdrop
          draws the design's 1px card borders without per-cell border rules */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-cardBorder border-y border-cardBorder [&>div]:bg-white">
          {sectors.map((sector) => (
            <SectorCard key={sector.key} sector={sector} />
          ))}
        </div>

        {/* Footer action */}
        <div className="p-4">
          <Link href="/brief-builder" className="block">
            <Button block size="large">
              Open Response Activities page per Inkhundla
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
};

export default ResponseActivities;
