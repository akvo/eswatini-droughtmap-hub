"use client";

import { InfoCircleOutlined } from "@ant-design/icons";
import { Spin } from "antd";
import PrecipitationChart from "@/components/Insights/WeatherTab/PrecipitationChart";
import TemperatureChart from "@/components/Insights/WeatherTab/TemperatureChart";
import useWeatherNormals from "@/hooks/useWeatherNormals";
import { useBrief } from "@/context/BriefContextProvider";
import BriefSection from "./BriefSection";
import CoverBlock from "./sections/CoverBlock";
import DclassSection from "./sections/DclassSection";
import SituationParagraph from "./sections/SituationParagraph";
import ExposureBars from "./sections/ExposureBars";
import ResponseAndNotify from "./sections/ResponseAndNotify";
import SourcesCredits from "./sections/SourcesCredits";

/**
 * Shown until an Inkhundla is applied (Figma 4159:191223). Identical to the
 * Detailed insights empty state, which is why the copy is kept in step rather
 * than reworded.
 */
export const SelectInkhundlaEmptyState = () => (
  <div className="flex min-h-[480px] w-full flex-col items-center justify-center gap-4 bg-white px-4 text-center">
    <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-cardBorder bg-white">
      <InfoCircleOutlined className="text-xl text-primary" />
    </div>
    <div className="flex flex-col gap-1">
      <h3 className="mb-0 text-2xl font-bold text-neutral-800">
        Select inkhundla
      </h3>
      <p className="mb-0 text-base text-neutral-500">
        Select inkhundla to see detailed insights
      </p>
    </div>
  </div>
);

/**
 * The assembled brief (Figma 4155:180002).
 *
 * One continuous document — a single white surface with divider rules — not a
 * stack of cards. Sections render in catalogue order regardless of the order
 * the user ticked them, so two briefs with the same components always read the
 * same way.
 */
// `data` comes from useBriefData in BriefBuilderPage rather than being fetched
// here: the forward slide-in needs the same cycle, and fetching in both places
// would double every request just to label a sentence.
const BriefPreview = ({ data }) => {
  const {
    applied,
    administrationId,
    selectedInkhundla,
    region,
    zone,
    inkhundlaResolving,
    inkhundlaUnknown,
  } = useBrief();
  const { cdi, risk, activities, loading } = data;
  // Range-independent, so fetched once here and shared by both charts —
  // exactly how WeatherTab wires them.
  const normals = useWeatherNormals(administrationId);

  const has = (key) => applied.components.includes(key);
  const period = cdi?.value?.period ?? cdi?.data?.[0]?.meta?.period ?? null;
  const dclass = cdi?.value?.dclass?.category ?? null;

  // Order matters: an unresolved id is not the same as no id, and neither is
  // the same as an id that turned out not to exist. Collapsing them is what
  // produced a spinner that never stopped.
  if (inkhundlaResolving) {
    return (
      <div className="flex min-h-[480px] flex-col items-center justify-center gap-3">
        <Spin size="large" />
        <span className="text-sm text-neutral-400">Loading Tinkhundla...</span>
      </div>
    );
  }

  if (inkhundlaUnknown) {
    return (
      <BriefSection
        bordered={false}
        isEmpty
        emptyText={`No Inkhundla matches "${applied.inkhundla}". Pick one from the list to build a brief.`}
      />
    );
  }

  if (!administrationId) {
    return <SelectInkhundlaEmptyState />;
  }

  if (loading) {
    return (
      <div className="flex min-h-[480px] flex-col items-center justify-center gap-3">
        <Spin size="large" />
        <span className="text-sm text-neutral-400">Building brief...</span>
      </div>
    );
  }

  if (!applied.components.length) {
    return (
      <BriefSection
        bordered={false}
        isEmpty
        emptyText="Choose at least one component, then press Apply."
      />
    );
  }

  return (
    <div id="brief-print-area" className="w-full">
      {(has("cover_header") || has("kpi_tiles")) && (
        <CoverBlock
          showHeader={has("cover_header")}
          showTiles={has("kpi_tiles")}
          name={selectedInkhundla}
          region={region}
          zone={cdi?.value?.zone || zone}
          cdi={cdi}
          risk={risk}
        />
      )}

      {has("situation_paragraph") && (
        <SituationParagraph name={selectedInkhundla} period={period} />
      )}

      {(has("dclass_strip_24m") || has("historic_comparison_note")) && (
        <DclassSection
          showStrip={has("dclass_strip_24m")}
          showNote={has("historic_comparison_note")}
          name={selectedInkhundla}
          cdi={cdi}
        />
      )}

      {/* Both charts are reused verbatim: TemperatureChart already renders
          T max / T min / T Mean with dashed 30-year averages, and ChartCard
          already carries the range picker (design doc D-9). */}
      {has("rainfall_12m") && (
        <div className="border-t border-cardBorder">
          <PrecipitationChart
            administrationId={administrationId}
            normals={normals}
          />
        </div>
      )}
      {has("temperature_12m") && (
        <div className="border-t border-cardBorder">
          <TemperatureChart
            administrationId={administrationId}
            normals={normals}
          />
        </div>
      )}

      {has("exposure_numbers") && <ExposureBars />}

      {(has("response_activities") || has("notify_list")) && (
        <ResponseAndNotify
          showActivities={has("response_activities")}
          showNotify={has("notify_list")}
          activities={activities}
        />
      )}

      {has("sources_credits") && (
        <SourcesCredits dclass={dclass} period={period} />
      )}
    </div>
  );
};

export default BriefPreview;
