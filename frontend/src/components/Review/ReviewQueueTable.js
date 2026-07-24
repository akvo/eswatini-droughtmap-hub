"use client";

import Link from "next/link";
import { Button, Input, Progress, Select, Table } from "antd";
import { TabButtons } from "@/components";
import { ConfidenceBadge, DroughtScore } from "@/components/DS";
import { PAGE_SIZE, REGION_OPTIONS } from "@/static/config";
import { useAppContext } from "@/context/AppContextProvider";
import { QUEUE_FILTERS, buildQueueQuery } from "@/lib/query";

/** SPI / LST readings. Mock until station data exists (backend is_mock). */
const StationSignals = ({ stations }) => {
  const signed = (n) => `${n > 0 ? "+" : ""}${n}`;
  return (
    <div
      title={
        stations?.is_mock
          ? "Provisional — placeholder station readings"
          : undefined
      }
      className="flex flex-col gap-0.5 text-sm leading-5"
    >
      <span className="flex gap-2">
        <span className="w-8 text-[#606060]">SPI</span>
        <span className="font-medium text-[#027A48]">
          {signed(stations?.spi)}
        </span>
      </span>
      <span className="flex gap-2">
        <span className="w-8 text-[#606060]">LST</span>
        <span className="font-medium text-[#B54708]">
          {signed(stations?.lst)} °C
        </span>
      </span>
    </div>
  );
};

const ReviewQueueTable = ({
  rows = [],
  total = 0,
  loading = false,
  state,
  isCompleted = false,
  reviewId,
  onChange,
  children,
}) => {
  // Zone vocabulary comes from the backend via /config.js (window.zones).
  const { zones } = useAppContext();
  const columns = [
    {
      title: "INKHUNDLA",
      dataIndex: "name",
      key: "name",
      render: (name, { region }) => (
        <div className="flex flex-col">
          <span className="font-medium text-[#333333]">{name}</span>
          <span className="text-sm text-[#a4a4a4]">{region}</span>
        </div>
      ),
    },
    {
      title: "CDI-E SCORE",
      dataIndex: "cdi_class",
      key: "cdi_class",
      width: 140,
      render: (level) => <DroughtScore level={level} />,
    },
    {
      title: "STATIONS VS SATELLITE",
      dataIndex: "stations_vs_satellite",
      key: "stations_vs_satellite",
      width: 200,
      render: (stations) => <StationSignals stations={stations} />,
    },
    {
      title: "CONFIDENCE",
      dataIndex: "confidence",
      key: "confidence",
      width: 150,
      render: (confidence) => (
        <span className="flex items-center gap-2">
          <ConfidenceBadge band={confidence?.band} />
          {confidence?.value != null && (
            <span
              className="text-sm text-[#606060]"
              title={
                confidence.is_mock ? "Provisional confidence value" : undefined
              }
            >
              {confidence.value}
            </span>
          )}
        </span>
      ),
    },
    {
      title: "REVIEWS",
      dataIndex: "reviews",
      key: "reviews",
      width: 180,
      render: ({ completed = 0, total: reviewers = 0 }) => (
        <div className="flex items-center gap-2">
          <Progress
            className="m-0"
            percent={reviewers ? (completed / reviewers) * 100 : 0}
            showInfo={false}
            size={["100%", 6]}
            strokeColor="#3E5EB9"
            trailColor="#EAECF0"
          />
          <span className="shrink-0 text-sm text-[#606060]">
            {completed}/{reviewers}
          </span>
        </div>
      ),
    },
    {
      title: "ACTIONS",
      key: "actions",
      width: 100,
      render: (_, record) => {
        // Carry the active queue filters so the individual page's Prev/Next
        // walks the same filtered order the reviewer sees (D-6).
        const qs = buildQueueQuery(state);
        return (
          <Link
            href={`/reviews/${reviewId}/${record?.administration_id}${
              qs ? `?${qs}` : ""
            }`}
          >
            <Button type="link" className="edm-reviews-action">
              {isCompleted ? "View" : "Review"}
            </Button>
          </Link>
        );
      },
    },
    {
      title: "D-CLASS",
      dataIndex: "my_suggestion",
      key: "my_suggestion",
      width: 110,
      align: "right",
      onCell: () => ({ style: { backgroundColor: "#ECEFF8" } }),
      // The reviewer's own class — what they approved or suggested. NOT
      // assigned_score, which stays empty until a validator signs the month off.
      render: (mine, { cdi_class }) => {
        if (!mine?.reviewed) {
          return (
            <span
              title="You have not reviewed this Inkhundla"
              className="text-[#a4a4a4]"
            >
              &mdash;
            </span>
          );
        }
        const suggested = mine.category !== cdi_class;
        return (
          <span
            className="inline-flex items-center gap-1"
            title={
              suggested
                ? `You suggested a different class${mine.comment ? `: ${mine.comment}` : ""}`
                : "You approved the computed class"
            }
          >
            <DroughtScore level={mine.category} />
            {suggested && <span className="text-[#B54708]">*</span>}
          </span>
        );
      },
    },
  ];

  return (
    <section className="w-full border border-[#eaecf0] bg-white">
      <div className="flex flex-col gap-4 border-b border-[#eaecf0] p-4 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-semibold leading-7 text-[#333333]">
          Review queue
        </h2>
        <Input.Search
          allowClear
          className="w-full sm:max-w-[320px]"
          placeholder="Search"
          defaultValue={state.search}
          onSearch={(search) => onChange({ search, page: 1 })}
        />
      </div>

      {children}

      <div className="flex flex-col gap-4 border-b border-[#eaecf0] p-4 xl:flex-row xl:items-center xl:justify-between">
        <TabButtons
          options={QUEUE_FILTERS}
          value={state.filter}
          onChange={(filter) => onChange({ filter, page: 1 })}
        />
        <div className="flex flex-wrap items-center gap-3">
          <Select
            className="min-w-[180px]"
            placeholder="All zones"
            allowClear
            options={zones}
            value={state.zone || undefined}
            onChange={(zone) => onChange({ zone: zone || "", page: 1 })}
          />
          <Select
            className="min-w-[180px]"
            placeholder="All regions"
            allowClear
            options={REGION_OPTIONS}
            value={state.region || undefined}
            onChange={(region) => onChange({ region: region || "", page: 1 })}
          />
        </div>
      </div>

      <Table
        className="edm-reviews-table"
        rowKey="administration_id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        tableLayout="fixed"
        scroll={{ x: 1100 }}
        pagination={
          total <= PAGE_SIZE
            ? false
            : {
                current: state.page,
                pageSize: PAGE_SIZE,
                total,
                align: "center",
                position: ["bottomCenter"],
                showSizeChanger: false,
                onChange: (page) => onChange({ page }),
              }
        }
      />
    </section>
  );
};

export default ReviewQueueTable;
