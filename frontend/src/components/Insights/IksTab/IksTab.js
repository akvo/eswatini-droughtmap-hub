"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import dynamic from "next/dynamic";
import {
  Spin,
  Result,
  Row,
  Col,
  Button,
  Tag,
  Table,
  Empty,
  Checkbox,
  Collapse,
  ConfigProvider,
} from "antd";
import { Line } from "akvo-charts";
import { api } from "@/lib/api";
import {
  IKS_INDICATOR_CATALOGUE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";

const IksHeatmap = dynamic(() => import("./IksHeatmap"), { ssr: false });

const { Panel } = Collapse;

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

const getRainfallPredictors = () => {
  const birds = [];
  const insects = [];
  const plants = [];
  const sky = [];

  Object.keys(IKS_INDICATOR_CATALOGUE).forEach((key) => {
    const item = IKS_INDICATOR_CATALOGUE[key];
    if (item.type === "rainfall") {
      const num = parseInt(key.split("__")[0], 10);
      const indicatorObj = {
        dbKey: key,
        name: item.label,
        isDroughtLeaning: item.meaning === "drought",
      };
      if (num <= 9) birds.push(indicatorObj);
      else if (num <= 12) insects.push(indicatorObj);
      else if (num <= 16) plants.push(indicatorObj);
      else sky.push(indicatorObj);
    }
  });

  return [
    { key: "b-birds", header: "Birds (Tinyoni)", indicators: birds },
    { key: "b-insects", header: "Insects & animals", indicators: insects },
    { key: "b-plants", header: "Plants & fruits", indicators: plants },
    { key: "b-sky", header: "Atmosphere & sky", indicators: sky },
  ];
};

const getSeasonalPredictors = () => {
  const animals = [];
  const plants = [];

  Object.keys(IKS_INDICATOR_CATALOGUE).forEach((key) => {
    const item = IKS_INDICATOR_CATALOGUE[key];
    if (item.type === "seasonal") {
      const num = parseInt(key.split("__")[0], 10);
      const indicatorObj = {
        dbKey: key,
        name: item.label,
        isDroughtLeaning: item.meaning === "drought",
      };
      if (num <= 5) animals.push(indicatorObj);
      else plants.push(indicatorObj);
    }
  });

  return [
    { key: "c-animals", header: "Birds & Animals", indicators: animals },
    { key: "c-plants", header: "Plants", indicators: plants },
  ];
};

const formatMonthLabel = (ymStr) => {
  if (!ymStr) return "";
  const parts = ymStr.split("-");
  if (parts.length < 2) return ymStr;
  const monthNum = parseInt(parts[1], 10);
  const shortMonths = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  return shortMonths[monthNum - 1] || "";
};

/**
 * Sub-component for individual KPI metric panel (Clean Code/DRY)
 */
const KpiMetricCard = ({ title, value, subtitle }) => (
  <div className="p-4 bg-white">
    <span className="text-[10px] text-neutral-400 font-bold block uppercase tracking-wider">
      {title}
    </span>
    <span className="text-2xl font-extrabold text-neutral-800 block mt-1">
      {value}
    </span>
    <span className="text-xs text-neutral-400 block mt-1">{subtitle}</span>
  </div>
);

/**
 * Reusable Monthly Status Grids component (Clean Code/DRY)
 */
const MonthlyStatusGrid = ({ title, subtitle, statesMap, legend, weeks }) => {
  const labels = weeks && weeks.length > 0 ? weeks : MONTHS;
  return (
    <div className="p-4 bg-white">
      <h4 className="text-sm font-bold text-neutral-800 mb-1">{title}</h4>
      <p className="text-xs text-neutral-400 mb-3">{subtitle}</p>
      <div
        className="flex flex-wrap gap-2 border-y border-neutral-100 py-4"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${labels.length}, minmax(0, 1fr))`,
        }}
      >
        {labels.map((m, idx) => {
          const state = statesMap(idx);
          let colorClass = "bg-neutral-200 text-neutral-500";
          if (state === "W" || state === "G")
            colorClass = "bg-[#12b76a] text-white"; // Green
          else if (state === "D" || state === "B")
            colorClass = "bg-[#b10d0b] text-white"; // Red
          else if (state === "M") colorClass = "bg-sky-200 text-sky-800";
          else if (state === "S") colorClass = "bg-amber-400 text-white";

          return (
            <div
              key={`${m}-${idx}`}
              className="flex flex-col items-center justify-center text-center"
            >
              <div
                className={`h-[34px] w-full flex items-center justify-center rounded-[4px] font-bold text-sm ${colorClass}`}
              >
                <span>{state}</span>
              </div>
              <span className="text-[10px] font-medium text-neutral-500 block uppercase opacity-85 mt-2">
                {m}
              </span>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-4 mt-3 text-[10px] text-neutral-400">
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 bg-neutral-200 block rounded-full"></span>{" "}
          No submission
        </span>
        {legend.map((item, idx) => (
          <span key={idx} className="flex items-center gap-1">
            <span
              className={`w-2.5 h-2.5 ${item.color} block rounded-full`}
            ></span>{" "}
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
};

/**
 * Sub-component for rendering indicator strips (Clean Code/DRY)
 */
const IndicatorRow = ({
  name,
  isDroughtLeaning = false,
  months = [],
  checkedMonths = [],
}) => {
  return (
    <div className="flex items-center justify-between py-2 border-b border-neutral-100 last:border-0 gap-4 bg-white px-4">
      <span className="text-xs text-neutral-700 font-medium truncate max-w-[280px]">
        {name}
      </span>
      <div className="flex gap-0.5">
        {(months.length > 0 ? months : Array(12).fill("")).map((m, idx) => {
          const observed = checkedMonths[idx] || false;
          const color = observed
            ? isDroughtLeaning
              ? "bg-red-500"
              : "bg-blue-600"
            : "bg-neutral-100";
          const label = m ? formatMonthLabel(m) : `Month ${idx + 1}`;
          return (
            <div
              key={idx}
              title={`${label}: ${observed ? "Observed" : "Not observed"}`}
              className={`w-3.5 h-3.5 rounded-[1px] ${color}`}
            />
          );
        })}
      </div>
    </div>
  );
};

const PredictorAccordion = ({
  title,
  subtitle,
  items,
  months = [],
  indicatorsData = {},
}) => (
  <div className="pb-6">
    <div className="px-4 mb-4">
      <h4 className="text-sm font-bold text-neutral-700">{title}</h4>
      <p className="text-xs text-neutral-400 mt-0.5">{subtitle}</p>
    </div>
    <div className="border-y border-neutral-200 bg-white">
      <Collapse
        bordered={false}
        expandIconPosition="end"
        className="bg-transparent"
      >
        {items.map((item) => (
          <Panel
            header={
              <span className="text-sm font-medium text-neutral-600">
                {item.header}
              </span>
            }
            key={item.key}
            className="border-b border-neutral-100 last:border-0 bg-white"
          >
            <div className="divide-y divide-neutral-100 bg-neutral-50 border-t border-neutral-100">
              {item.indicators.map((ind, i) => (
                <IndicatorRow
                  key={i}
                  name={ind.name}
                  isDroughtLeaning={ind.isDroughtLeaning}
                  months={months}
                  checkedMonths={indicatorsData[ind.dbKey] || []}
                />
              ))}
            </div>
          </Panel>
        ))}
      </Collapse>
    </div>
  </div>
);

const IksTab = ({
  selectedInkhundla = "Mhlangatane",
  administrationId = null,
  region = "",
  zone = "",
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [regionMap, setRegionMap] = useState({});
  const [data, setData] = useState({
    netSignal: null,
    soilTrend: null,
  });
  const [catalogueRows, setCatalogueRows] = useState([]);
  const [heatmapData, setHeatmapData] = useState({});
  const [startIndex, setStartIndex] = useState(0);
  const [chartReady, setChartReady] = useState(false);
  const [showRain, setShowRain] = useState(true);
  const [showDrought, setShowDrought] = useState(true);

  const [stats, setStats] = useState({
    total_reports_received: 0,
    total_months_drought: 0,
    reporting_consistency_percentage: 0.0,
    validation_rate_percentage: 0.0,
    average_validation_time_days: 0.0,
    form_completion_percentage: 0.0,
    zone: zone,
    indicator_activity: {
      months: [],
      rain_leaning: [],
      extreme_weather: [],
    },
  });
  const [bulkSeries, setBulkSeries] = useState({
    months: [],
    indicators: {},
  });
  const [photos, setPhotos] = useState([]);

  useEffect(() => {
    if (!loading) {
      const handle = setTimeout(() => {
        setChartReady(true);
      }, 100);
      return () => clearTimeout(handle);
    } else {
      setChartReady(false);
    }
  }, [loading, administrationId]);

  const handlePrev = () => {
    setStartIndex((prev) => Math.max(0, prev - 1));
  };

  const handleNext = () => {
    setStartIndex((prev) => Math.max(0, Math.min(photos.length - 3, prev + 1)));
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [netSignal, soilTrend, indicatorCounts, agreement, heatmap] =
          await Promise.all([
            api("GET", "/iks/aggregations/net-signal"),
            api("GET", "/iks/aggregations/soil-trend"),
            api("GET", "/iks/aggregations/indicator-counts"),
            api("GET", "/iks/aggregations/agreement"),
            api("GET", "/iks/aggregations/heatmap"),
          ]);

        setRegionMap(soilTrend.region_map || {});
        setHeatmapData(heatmap || {});

        const countMap = {};
        (indicatorCounts?.data || []).forEach((row) => {
          countMap[row.indicator] = row.submission_count;
        });
        const catalogue = Object.keys(IKS_INDICATOR_CATALOGUE).map(
          (key, i) => ({
            key: String(i + 1),
            code: IKS_INDICATOR_CATALOGUE[key].code,
            label: IKS_INDICATOR_CATALOGUE[key].label,
            type: IKS_INDICATOR_CATALOGUE[key].type,
            meaning: IKS_INDICATOR_CATALOGUE[key].meaning,
            submission_count: countMap[i + 1] ?? 0,
          }),
        );
        setCatalogueRows(catalogue);

        setData({ netSignal, soilTrend });

        if (administrationId) {
          const [adminStats, adminSeries, adminPhotos] = await Promise.all([
            api("GET", `/iks/${administrationId}/stats`),
            api("GET", `/iks/${administrationId}/series?bulk=true`),
            api("GET", `/iks/${administrationId}/photos`),
          ]);
          setStats(adminStats);
          setBulkSeries(adminSeries);
          setPhotos(adminPhotos?.photos || []);
        } else {
          setStats({
            total_reports_received: 0,
            total_months_drought: 0,
            reporting_consistency_percentage: 0.0,
            validation_rate_percentage: 0.0,
            average_validation_time_days: 0.0,
            form_completion_percentage: 0.0,
            zone: zone,
            indicator_activity: {
              months: Array.from({ length: 12 }, (_, i) => `Month ${i + 1}`),
              rain_leaning: Array(12).fill(0),
              extreme_weather: Array(12).fill(0),
            },
          });
          setBulkSeries({
            months: Array.from({ length: 12 }, (_, i) => `Month ${i + 1}`),
            indicators: {},
          });
          setPhotos([]);
        }
      } catch (err) {
        console.error("Failed to load IKS data:", err);
        setError(err.message || "An error occurred while fetching IKS data.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [administrationId]);

  if (loading) {
    return (
      <div className="w-full h-96 flex flex-col items-center justify-center gap-4">
        <Spin size="large" />
        <span className="text-neutral-500 font-medium">
          Fetching Indigenous Knowledge data...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <Result
        status="error"
        title="Failed to Load IKS Data"
        subTitle={error}
        className="my-8"
      />
    );
  }

  const consistency = stats.reporting_consistency_percentage || 0;
  const validationRate = stats.validation_rate_percentage || 0;
  const validationTime = stats.average_validation_time_days || 0;
  const completionRate = stats.form_completion_percentage || 0;
  const droughtCategoryVal =
    stats.total_months_drought >= 8
      ? DROUGHT_CATEGORY_VALUE.d3
      : stats.total_months_drought >= 4
        ? DROUGHT_CATEGORY_VALUE.d2
        : DROUGHT_CATEGORY_VALUE.d1;

  const droughtLevel = (dCategoryVal) =>
    dCategoryVal === DROUGHT_CATEGORY_VALUE.d3
      ? "D3"
      : dCategoryVal === DROUGHT_CATEGORY_VALUE.d2
        ? "D2"
        : "D1";

  const droughtBadgeColor = DROUGHT_CATEGORY_COLOR[droughtCategoryVal];
  const droughtLabelText = DROUGHT_CATEGORY_LABEL[droughtCategoryVal];
  const droughtBadgeTextColor =
    droughtCategoryVal === DROUGHT_CATEGORY_VALUE.d1 ? "#7c5a00" : "#ffffff";

  const badgeParentBgMap = {
    [DROUGHT_CATEGORY_VALUE.normal]: "#f0fdf4",
    [DROUGHT_CATEGORY_VALUE.d0]: "#fefce8",
    [DROUGHT_CATEGORY_VALUE.d1]: "#fef9c3",
    [DROUGHT_CATEGORY_VALUE.d2]: "#ffedd5",
    [DROUGHT_CATEGORY_VALUE.d3]: "#f7e7e7",
    [DROUGHT_CATEGORY_VALUE.d4]: "#f7e7e7",
    [DROUGHT_CATEGORY_VALUE.none]: "#f9fafb",
  };
  const parentBg = badgeParentBgMap[droughtCategoryVal] || "#f9fafb";

  const zoneLabel = stats.zone
    ? stats.zone
        .split("_")
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ")
    : zone
      ? zone
          .split("_")
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(" ")
      : "";

  // Derive date range from first and last weeks in the DB payload
  const dbWeeks = data.netSignal?.weeks || [];
  const firstWeek = dbWeeks[0] || "";
  const lastWeek = dbWeeks[dbWeeks.length - 1] || "";
  const dateRange =
    firstWeek && lastWeek
      ? `${firstWeek} - ${lastWeek} ${new Date().getFullYear()}`
      : "";

  const getSoilState = (idx) => {
    const st = data.soilTrend?.soil_trend;
    if (!st || !st.dry || !st.moist || !st.wet) return "-";
    const d = st.dry[idx] || 0;
    const m = st.moist[idx] || 0;
    const w = st.wet[idx] || 0;
    if (w >= m && w >= d) return "W";
    if (d >= w && d >= m) return "D";
    return "M";
  };

  const getVegState = (idx) => {
    const vt = data.soilTrend?.veg_trend;
    if (!vt || !vt.green || !vt.some || !vt.brown) return "-";
    const g = vt.green[idx] || 0;
    const s = vt.some[idx] || 0;
    const b = vt.brown[idx] || 0;
    if (g >= s && g >= b) return "G";
    if (s >= g && s >= b) return "S";
    return "B";
  };

  const chartMonths = stats.indicator_activity?.months || [];
  const rainLeaningData = stats.indicator_activity?.rain_leaning || [];
  const extremeWeatherData = stats.indicator_activity?.extreme_weather || [];

  const activitySeries = [
    {
      name: "Rainfall Predictors (Section B)",
      type: "line",
      data: rainLeaningData,
      itemStyle: { color: "#3E5EB9" },
      lineStyle: { width: 2 },
      symbol: "circle",
      symbolSize: 6,
      smooth: true,
      areaStyle: {
        color: {
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: "rgba(62, 94, 185, 0.15)" },
            { offset: 1, color: "rgba(62, 94, 185, 0.01)" },
          ],
        },
      },
    },
    {
      name: "Extreme Weather (Section C)",
      type: "line",
      data: extremeWeatherData,
      itemStyle: { color: "#E60000" },
      lineStyle: { width: 2 },
      symbol: "circle",
      symbolSize: 6,
      smooth: true,
      areaStyle: {
        color: {
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: "rgba(230, 0, 0, 0.15)" },
            { offset: 1, color: "rgba(230, 0, 0, 0.01)" },
          ],
        },
      },
    },
  ];

  const activityOptions = {
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: "#e5e7eb",
      borderWidth: 1,
      textStyle: { color: "#1f2937" },
    },
    legend: {
      show: false,
    },
    grid: {
      top: 25,
      left: "3%",
      right: "4%",
      bottom: "10%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: chartMonths.map(formatMonthLabel),
      axisLine: { lineStyle: { color: "#e5e7eb" } },
      axisLabel: { color: "#6b7280", rotate: 30 },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: "#f3f4f6" } },
      axisLabel: { color: "#6b7280" },
    },
    series: activitySeries.filter(
      (s, i) => (i === 0 && showRain) || (i === 1 && showDrought),
    ),
  };

  // Catalogue table columns (spec section 6)
  const catalogueColumns = [
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      width: 70,
      render: (v) => (
        <span className="font-mono text-xs font-bold text-neutral-700">
          {v}
        </span>
      ),
    },
    {
      title: "Indicator",
      dataIndex: "label",
      key: "label",
      render: (v) => <span className="text-xs text-neutral-700">{v}</span>,
    },
    {
      title: "Type",
      dataIndex: "type",
      key: "type",
      width: 90,
      render: (v) => (
        <Tag
          color={v === "rainfall" ? "blue" : "orange"}
          className="text-[10px] capitalize"
        >
          {v}
        </Tag>
      ),
    },
    {
      title: "Predicts",
      dataIndex: "meaning",
      key: "meaning",
      width: 90,
      render: (v) => (
        <Tag
          color={v === "rain" ? "cyan" : "volcano"}
          className="text-[10px] capitalize"
        >
          {v}
        </Tag>
      ),
    },
    {
      title: "Submissions",
      dataIndex: "submission_count",
      key: "submission_count",
      width: 100,
      align: "right",
      render: (v) => (
        <span className="font-semibold text-xs text-neutral-800">{v}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6 w-full -mt-6">
      <div className="bg-white">
        {/* Inkhundla Header */}
        <div className="flex items-center justify-between border-b border-neutral-100 px-4 pt-10 pb-6">
          <div>
            <h2 className="text-2xl font-bold text-neutral-800">
              {selectedInkhundla} Inkhundla
            </h2>
            <p className="text-sm text-neutral-400 font-medium">
              {region}
              {zoneLabel ? ` - ${zoneLabel}` : ""}
            </p>
          </div>
          {/* Badge Group matching Figma spec node-4116_96303 (compact version) */}
          <div
            style={{
              backgroundColor: parentBg,
            }}
            className="flex gap-[8px] items-center pl-[2px] pr-[8px] py-[2px] rounded-[6px]"
          >
            {/* Inner DroughtClassAndConfidence block */}
            <div
              style={{
                backgroundColor: droughtBadgeColor,
              }}
              className="flex items-center justify-center px-[4px] py-[1px] rounded-[4px] shrink-0 w-[36px]"
            >
              <p className="font-['Inter'] font-semibold leading-[18px] text-[13px] text-center text-white whitespace-nowrap mb-0">
                {droughtLevel(droughtCategoryVal)}
              </p>
            </div>
            {/* Label block */}
            <div className="flex gap-[4px] items-center">
              <span className="font-['Inter'] font-normal leading-[18px] text-[13px] text-[#333] whitespace-nowrap">
                {droughtLabelText}
              </span>
            </div>
          </div>
        </div>

        {/* 2 KPI metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 bg-white divide-y md:divide-y-0 md:divide-x divide-neutral-100 overflow-hidden shadow-sm border-b border-neutral-100">
          <KpiMetricCard
            title="Reporting consistency"
            value={`${consistency}%`}
            subtitle="12 / 12 months reported"
          />
          <KpiMetricCard
            title="Form completion"
            value={`${completionRate}%`}
            subtitle="Sections B + C + D filled"
          />
        </div>

        {/* Line Chart Panel */}
        <div className="px-4 py-6 border-b border-neutral-100">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="text-sm font-bold text-neutral-800">
                Indicator activity per monthly report
              </h4>
              <p className="text-xs text-neutral-400">
                How many rain-leaning vs drought-leaning indicators the citizen
                scientist ticked each month
              </p>
            </div>
            <span className="text-xs text-neutral-400 font-medium border border-neutral-100 px-2 py-1 rounded bg-neutral-50">
              {dateRange}
            </span>
          </div>

          {/* Interactive Checkbox Filters */}
          <div className="flex items-center gap-6 mb-4">
            <ConfigProvider theme={{ token: { colorPrimary: "#3E5EB9" } }}>
              <Checkbox
                checked={showRain}
                onChange={(e) => setShowRain(e.target.checked)}
              >
                <span className="text-xs font-semibold text-neutral-600">
                  Rain-leaning
                </span>
              </Checkbox>
            </ConfigProvider>
            <ConfigProvider theme={{ token: { colorPrimary: "#E60000" } }}>
              <Checkbox
                checked={showDrought}
                onChange={(e) => setShowDrought(e.target.checked)}
              >
                <span className="text-xs font-semibold text-neutral-600">
                  Drought-leaning
                </span>
              </Checkbox>
            </ConfigProvider>
          </div>

          <div className="w-full h-80 pt-4">
            {chartReady ? (
              <Line rawConfig={activityOptions} />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Spin tip="Rendering Chart..." />
              </div>
            )}
          </div>
          {chartReady && (
            <div className="flex justify-center gap-6 mt-1 mb-4">
              <div
                className={`flex items-center gap-2 text-xs transition-opacity duration-200 ${showRain ? "opacity-100" : "opacity-35"}`}
              >
                <span className="w-2.5 h-2.5 rounded-full bg-[#3E5EB9] block" />
                <span className="font-medium text-neutral-500">
                  Rain-leaning
                </span>
              </div>
              <div
                className={`flex items-center gap-2 text-xs transition-opacity duration-200 ${showDrought ? "opacity-100" : "opacity-35"}`}
              >
                <span className="w-2.5 h-2.5 rounded-full bg-[#E60000] block" />
                <span className="font-medium text-neutral-500">
                  Drought-leaning
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Soil Moisture and Vegetation Grids (DRY) */}
        <Row className="border-b border-neutral-100">
          <Col md={24} className="border-r border-neutral-100">
            <MonthlyStatusGrid
              title="Soil moisture (Womile / Ubutsile / Umanti)"
              subtitle="one answer per monthly report"
              statesMap={getSoilState}
              weeks={data.soilTrend?.weeks}
              legend={[
                { color: "bg-sky-200", label: "W-Wet" },
                { color: "bg-amber-400", label: "M-Moist" },
                { color: "bg-red-600", label: "D-Dry" },
              ]}
            />
          </Col>

          <Col md={24}>
            <MonthlyStatusGrid
              title="D2 vegetation greenness (Tiluhlata / Timbalwa letiluhlata / Bushile)"
              subtitle="one answer per monthly report"
              statesMap={getVegState}
              weeks={data.soilTrend?.weeks}
              legend={[
                { color: "bg-[#12b76a]", label: "G-Generally green" },
                { color: "bg-amber-400", label: "S-Some green" },
                { color: "bg-[#b10d0b]", label: "B-Brown" },
              ]}
            />
          </Col>
        </Row>

        {/* Flat Indicator Lists */}
        <div className="space-y-0 py-6 border-b border-neutral-100">
          <PredictorAccordion
            title="Section B: Rainfall predictors (21 indicators)"
            subtitle="One strip per indicator · each cell = one monthly report"
            items={getRainfallPredictors()}
            months={bulkSeries.months}
            indicatorsData={bulkSeries.indicators}
          />
          <PredictorAccordion
            title="Section C: Seasonal & extreme-weather predictors (8 indicators)"
            subtitle="Signs of drought, floods, storms · one strip per indicator"
            items={getSeasonalPredictors()}
            months={bulkSeries.months}
            indicatorsData={bulkSeries.indicators}
          />
        </div>

        {/* Photos Grid Carousel */}
        <div className="border-b border-neutral-100 px-4 py-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="text-sm font-bold text-neutral-800">
                Submitted photos
              </h4>
              <p className="text-xs text-neutral-400">
                Photos uploaded with monthly Kobo reports | click to view full |{" "}
                {photos.length} photos found
              </p>
            </div>
            <Button
              type="default"
              className="text-neutral-600 font-semibold border-neutral-200"
            >
              Add photo
            </Button>
          </div>
          {photos.length === 0 ? (
            <Empty description="No photos submitted" />
          ) : (
            <>
              <Row gutter={[16, 16]}>
                {photos.slice(startIndex, startIndex + 3).map((photo, i) => (
                  <Col xs={24} sm={8} key={i}>
                    <div className="relative group overflow-hidden rounded-lg border border-neutral-100 shadow-sm cursor-pointer h-48 bg-neutral-100">
                      <Image
                        src={photo.url}
                        alt={photo.title || "Observation Photo"}
                        fill
                        unoptimized
                        sizes="(max-width: 768px) 100vw, 33vw"
                        className="object-cover transition-transform duration-300 group-hover:scale-105"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent flex flex-col justify-end p-4">
                        <span className="text-white text-xs font-bold">
                          {photo.title || "Observation Photo"}
                        </span>
                        <span className="text-neutral-300 text-[10px] mt-1">
                          {photo.date || "Unknown Date"}
                        </span>
                      </div>
                    </div>
                  </Col>
                ))}
              </Row>
              <div className="flex items-center gap-2 mt-4">
                <Button
                  onClick={handlePrev}
                  disabled={startIndex === 0}
                  type="default"
                  className="text-neutral-600 font-semibold border-neutral-200 px-3 py-1 flex items-center justify-center rounded"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M15 19l-7-7 7-7"
                    />
                  </svg>
                </Button>
                <Button
                  onClick={handleNext}
                  disabled={startIndex >= photos.length - 3}
                  type="default"
                  className="text-neutral-600 font-semibold border-neutral-200 px-3 py-1 flex items-center justify-center rounded"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </Button>
              </div>
            </>
          )}
        </div>

        {/* Indicator Catalogue Table - spec UAC */}
        <div className="border-t border-neutral-100 px-4 py-6">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-neutral-800">
              Indicator catalogue
            </h4>
            <p className="text-xs text-neutral-400">
              29 indicators | submission counts derived from regional averages |
              matches IKS-1 aggregation output
            </p>
          </div>
          {catalogueRows.length === 0 ? (
            <Empty description="No indicator data" />
          ) : (
            <Table
              dataSource={catalogueRows}
              columns={catalogueColumns}
              pagination={false}
              size="small"
              className="text-xs"
              scroll={{ x: 600 }}
            />
          )}
        </div>

        {/* Inkhundla x Week Heatmap - spec UAC (non-blocking via dynamic import) */}
        <div className="border-t border-neutral-100 px-4 py-6">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-neutral-800">
              Inkhundla x week submission heatmap
            </h4>
            <p className="text-xs text-neutral-400">
              Hover a cell to see Inkhundla name, week and submission count
            </p>
          </div>
          <IksHeatmap data={heatmapData} />
        </div>
      </div>
    </div>
  );
};

export default IksTab;
