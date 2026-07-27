"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  Spin,
  Result,
  Row,
  Col,
  Button,
  Tag,
  // Table,
  Empty,
  Checkbox,
  ConfigProvider,
  Image,
} from "antd";
import { Line } from "akvo-charts";
import { api } from "@/lib/api";
import { IKS_INDICATOR_CATALOGUE } from "@/static/config";
import InkhundlaHeader from "../InkhundlaHeader";
import TabLoader from "../TabLoader";
import KpiMetricCard from "./KpiMetricCard";
import MonthlyStatusGrid from "./MonthlyStatusGrid";
import { formatMonthLabel } from "./IndicatorRow";
import { CalendarOutlined, DownOutlined } from "@ant-design/icons";

import PredictorAccordion from "./PredictorAccordion";
import {
  getRainfallPredictors,
  getSeasonalPredictors,
  formatPercentage,
} from "./iksUtils";

// const IksHeatmap = dynamic(() => import("./IksHeatmap"), { ssr: false });

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
  }, [administrationId, zone]);

  if (loading) {
    return <TabLoader tip="Fetching Indigenous Knowledge data..." />;
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

  const consistency = stats.reporting_consistency_percentage;
  const isLocked = consistency === null || consistency === undefined;
  const reportedMonthsCount = isLocked
    ? 0
    : Math.round((consistency / 100) * 12);
  const completionRate = stats.form_completion_percentage;

  // Derive date range from first and last weeks in the DB payload
  const dbWeeks = data.netSignal?.weeks || [];
  const firstWeek = dbWeeks[0] || "";
  const lastWeek = dbWeeks[dbWeeks.length - 1] || "";
  const dateRange =
    firstWeek && lastWeek
      ? `${firstWeek} - ${lastWeek} ${new Date().getFullYear()}`
      : "";

  // A week with no submission comes back as 0/0/0. Fall through to "-"
  // ("No submission") rather than letting the >= comparisons below pick a
  // winner out of three zeroes.
  const getSoilState = (idx) => {
    const st = data.soilTrend?.soil_trend;
    if (!st || !st.dry || !st.moist || !st.wet) return "-";
    const d = st.dry[idx] || 0;
    const m = st.moist[idx] || 0;
    const w = st.wet[idx] || 0;
    if (d + m + w === 0) return "-";
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
    if (g + s + b === 0) return "-";
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
      itemStyle: { color: "#B10D0B" },
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
            { offset: 0, color: "rgba(177, 13, 11, 0.15)" },
            { offset: 1, color: "rgba(177, 13, 11, 0.01)" },
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
      textStyle: { color: "#1f2937", fontSize: 13 },
      padding: [8, 12],
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
      splitLine: { lineStyle: { color: "#e5e7eb", type: "dashed" } },
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
    <div className="space-y-6 w-full">
      <div className="bg-white border border-cardBorder border-t-0">
        <InkhundlaHeader
          name={selectedInkhundla}
          region={region}
          zone={stats.zone || zone}
          dclass={stats.cdi_d_class ?? null}
        />

        {/* 2 KPI metrics */}
        {!isLocked && (
          <div className="grid grid-cols-1 md:grid-cols-2 bg-white divide-y md:divide-y-0 md:divide-x divide-cardBorder overflow-hidden border-b border-cardBorder">
            <KpiMetricCard
              title="Reporting consistency"
              value={`${formatPercentage(consistency)}%`}
              subtitle={`${reportedMonthsCount} / 12 months reported`}
              locked={isLocked}
            />
            <KpiMetricCard
              title="Form completion"
              value={`${formatPercentage(completionRate)}%`}
              subtitle="Sections B + C + D filled"
              locked={isLocked}
            />
          </div>
        )}

        <div className="px-4 py-4 border-b border-cardBorder">
          <div className="flex items-center justify-between border-b border-cardBorder pb-4 mb-4">
            <div>
              <h4 className="text-[16px] font-bold text-neutral-800 leading-[30px] mb-0">
                Indicator activity per monthly report
              </h4>
              <p className="text-[14px] text-[#606060] font-normal mt-1 mb-0">
                How many rain-leaning vs extreme weather-leaning indicators the
                citizen scientist ticked each month
              </p>
            </div>
            <div className="flex items-center gap-2 border border-cardBorder px-3 py-1.5 rounded bg-white text-sm text-[#333] shrink-0 select-none">
              <CalendarOutlined className="text-neutral-400" />
              <span className="font-normal text-[14px] leading-none">
                {dateRange}
              </span>
              {/* <DownOutlined className="text-neutral-400 text-[10px] ml-1" /> */}
            </div>
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
            <ConfigProvider theme={{ token: { colorPrimary: "#B10D0B" } }}>
              <Checkbox
                checked={showDrought}
                onChange={(e) => setShowDrought(e.target.checked)}
              >
                <span className="text-xs font-semibold text-neutral-600">
                  Extreme weather-leaning
                </span>
              </Checkbox>
            </ConfigProvider>
          </div>

          <div className="w-full h-[380px] pt-4">
            {chartReady ? (
              <Line rawConfig={activityOptions} />
            ) : (
              <div className="w-full h-full flex flex-col gap-2 items-center justify-center">
                {/* `tip` needs Spin's nest/fullscreen pattern — the label is
                    a sibling instead. */}
                <Spin />
                <span className="text-sm text-neutral-400">
                  Rendering Chart...
                </span>
              </div>
            )}
          </div>
          {chartReady && (
            <div className="flex justify-center gap-6 mt-2 mb-2">
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
                <span className="w-2.5 h-2.5 rounded-full bg-[#B10D0B] block" />
                <span className="font-medium text-neutral-500">
                  Extreme weather-leaning
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Soil Moisture and Vegetation Grids (DRY) */}
        <Row className="border-b border-cardBorder">
          <Col md={24} className="border-b border-cardBorder">
            <MonthlyStatusGrid
              title="Soil moisture (Womile / Ubutsile / Umanti)"
              subtitle="one answer per monthly report"
              statesMap={getSoilState}
              weeks={data.soilTrend?.weeks}
              legend={[
                { color: "bg-[#12b76a]", label: "W-Wet" },
                { color: "bg-[#f39c12]", label: "M-Moist" },
                { color: "bg-[#b10d0b]", label: "D-Dry" },
              ]}
            />
          </Col>

          <Col md={24}>
            <MonthlyStatusGrid
              title="Vegetation greenness (Tiluhlata / Timbalwa letiluhlata / Bushile)"
              subtitle="one answer per monthly report"
              statesMap={getVegState}
              weeks={data.soilTrend?.weeks}
              legend={[
                { color: "bg-[#12b76a]", label: "G-Generally green" },
                { color: "bg-[#f39c12]", label: "S-Some green" },
                { color: "bg-[#b10d0b]", label: "B-Brown" },
              ]}
            />
          </Col>
        </Row>

        {/* Flat Indicator Lists */}
        <div className="space-y-6 pt-6 pb-0">
          <PredictorAccordion
            title="Section B: Rainfall predictors (21 indicators)"
            subtitle="One strip per indicator · each cell = one monthly report"
            items={getRainfallPredictors()}
            months={bulkSeries.months}
            indicatorsData={bulkSeries.indicators}
            section="B"
          />
          <PredictorAccordion
            title="Section C: Seasonal & extreme-weather predictors (8 indicators)"
            subtitle="Signs of drought, floods, storms · one strip per indicator"
            items={getSeasonalPredictors()}
            months={bulkSeries.months}
            indicatorsData={bulkSeries.indicators}
            section="C"
          />
        </div>
      </div>

      <div className="bg-white border border-cardBorder py-4">
        <div className="flex items-center justify-between border-b border-cardBorder px-4 pb-4 mb-4">
          <div>
            <h4 className="text-[20px] font-bold text-neutral-800 leading-[30px] mb-0">
              Submitted photos
            </h4>
            <p className="text-sm text-[#606060] font-normal mt-1 mb-0">
              Photos uploaded with monthly Kobo reports · click to view full ·{" "}
              {photos.length} photos found
            </p>
          </div>
        </div>
        <div className="px-4">
          {photos.length === 0 ? (
            <Empty description="No photos submitted" />
          ) : (
            <>
              <Image.PreviewGroup>
                <Row gutter={[16, 16]}>
                  {photos.slice(startIndex, startIndex + 3).map((photo, i) => (
                    <Col xs={24} sm={8} key={i}>
                      <div className="relative group overflow-hidden rounded-lg border border-cardBorder cursor-pointer h-48 bg-neutral-100">
                        <Image
                          src={photo.url}
                          alt={photo.title || "Observation Photo"}
                          className="!w-full !h-full object-cover transition-transform duration-300 group-hover:scale-105"
                          preview={{
                            mask: (
                              <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity">
                                <svg
                                  className="w-8 h-8 text-white"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                  strokeWidth={2}
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"
                                  />
                                </svg>
                              </div>
                            ),
                          }}
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent flex flex-col justify-end p-4 pointer-events-none">
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
              </Image.PreviewGroup>
              <div className="flex items-center gap-2 mt-4">
                <Button
                  onClick={handlePrev}
                  disabled={startIndex === 0}
                  type="default"
                  className="text-neutral-600 font-semibold border-cardBorder px-3 py-1 flex items-center justify-center rounded"
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
                  className="text-neutral-600 font-semibold border-cardBorder px-3 py-1 flex items-center justify-center rounded"
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
      </div>

      {/* Indicator Catalogue Table - spec UAC */}
      {/* <div className="border-t border-neutral-100 px-4 py-6">
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
        </div> */}

      {/* Inkhundla x Week Heatmap - spec UAC (non-blocking via dynamic import) */}
      {/* <div className="border-t border-neutral-100 px-4 py-6">
          <div className="mb-4">
            <h4 className="text-sm font-bold text-neutral-800">
              Inkhundla x week submission heatmap
            </h4>
            <p className="text-xs text-neutral-400">
              Hover a cell to see Inkhundla name, week and submission count
            </p>
          </div>
          <IksHeatmap data={heatmapData} />
        </div> */}
    </div>
  );
};

export default IksTab;
