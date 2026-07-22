"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Avatar, Button, Input, Progress, Table, Tag, Tooltip } from "antd";
import {
  CalendarOutlined,
  SearchOutlined,
  LeftOutlined,
} from "@ant-design/icons";
import { Can, FeedbackSection, TabButtons } from "@/components";
import { MetricCard } from "@/components/DS";
import { PAGE_SIZE, DROUGHT_CATEGORY_CODE } from "@/static/config";
import { validationSummary, validationQueue } from "@/static/mocks/validation";
import dayjs from "dayjs";
import PublishModal from "./PublishModal";

const STATUS_FILTERS = [
  { label: "All", value: "all" },
  { label: "Ready", value: "ready" },
  { label: "Awaiting review", value: "awaiting" },
  { label: "Validated", value: "validated" },
];

const STATUS_CONFIG = {
  ready: { label: "Ready", color: "#f39c12" },
  awaiting: { label: "Awaiting", color: "#3b82f6" },
  validated: { label: "Validated", color: "#12b76a" },
};

const StatusBadge = ({ status, total }) => {
  const config = STATUS_CONFIG[status] || {
    label: "Unknown",
    color: "#999",
  };
  const suffix =
    status === "awaiting" && total
      ? ` ${total} review${total > 1 ? "s" : ""}`
      : "";
  return (
    <Tag className="edm-reviews-status-tag" color={config.color}>
      {config.label}
      {suffix}
    </Tag>
  );
};

const ReviewerAvatars = ({ reviewers = [] }) => (
  <div className="flex items-center gap-1">
    <span className="text-sm text-[#606060] mr-1">
      {reviewers.length} user{reviewers.length !== 1 ? "s" : ""}
    </span>
    <Avatar.Group
      max={{
        count: 5,
        style: { backgroundColor: "#3E5EB9", fontSize: 11 },
      }}
      size={24}
    >
      {reviewers.map((r) => (
        <Tooltip key={r.id} title={r.label}>
          <Avatar
            size={24}
            style={{ backgroundColor: "#3E5EB9", fontSize: 11 }}
          >
            {r.label}
          </Avatar>
        </Tooltip>
      ))}
    </Avatar.Group>
  </div>
);

const VALIDATION_DCLASS_COLOR = {
  0: "#CAF3DB", // Normal — Success-100
  1: "#CAF3DB", // D0 — Success-100
  2: "#FBEFBF", // D1 — Primary-100
  3: "#F7D4B5", // D2 — Accent-100 (close to D3 design)
  4: "#F7D4B5", // D3 — Accent-100
  5: "#F7C3BE", // D4 — Error-100
};

const DClassBadge = ({ level }) => {
  const bg = VALIDATION_DCLASS_COLOR[level] ?? "#f3f4f6";
  const code = DROUGHT_CATEGORY_CODE?.[level] ?? "—";
  return (
    <span
      className="inline-flex items-center justify-center rounded font-semibold h-[22px] min-w-[40px] px-1.5 text-xs"
      style={{ backgroundColor: bg, color: "#20232D" }}
    >
      {code}
    </span>
  );
};

const DClassSpread = ({ levels = [] }) => (
  <div className="flex items-center gap-1">
    {levels.map((level, i) => (
      <DClassBadge key={i} level={level} />
    ))}
  </div>
);

const ValidationDetailPage = () => {
  const { id } = useParams();
  const router = useRouter();

  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [publishOpen, setPublishOpen] = useState(false);

  // TODO: replace mock with API call: GET /admin/publication/{id}/validation-summary
  const summary = validationSummary;
  // TODO: replace mock with API call: GET /admin/publication/{id}/validation-queue
  const queue = validationQueue;

  const allValidated = useMemo(() => {
    const validated = summary.data.find((d) => d.key === "validated");
    const awaiting = summary.data.find((d) => d.key === "awaiting");
    return validated?.value > 0 && awaiting?.value === 0;
  }, [summary]);

  const filteredData = useMemo(() => {
    let rows = queue.data;
    if (statusFilter !== "all") {
      rows = rows.filter((r) => r.status === statusFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(
        (r) =>
          r.label.toLowerCase().includes(q) ||
          r.group.toLowerCase().includes(q),
      );
    }
    return rows;
  }, [queue.data, statusFilter, search]);

  const publishedDate = summary.published_at
    ? dayjs(summary.published_at).format("D MMMM YYYY")
    : null;

  const columns = [
    {
      title: "INKHUNDLA",
      dataIndex: "label",
      key: "label",
      width: 160,
      fixed: "left",
      render: (value, record) => (
        <div>
          <div className="font-medium text-[#333333]">{value}</div>
          <div className="text-xs text-[#606060]">{record.group}</div>
        </div>
      ),
    },
    {
      title: "REVIEWS",
      key: "reviews",
      width: 80,
      render: (_, record) => (
        <span className="text-sm">
          {record.reviews_completed}/{record.reviews_total}
        </span>
      ),
    },
    {
      title: "REVIEWER MIX",
      key: "reviewer_mix",
      width: 160,
      render: (_, record) => <ReviewerAvatars reviewers={record.reviewers} />,
    },
    {
      title: "D-CLASS SPREAD",
      key: "dclass_spread",
      width: 200,
      render: (_, record) => <DClassSpread levels={record.dclass_spread} />,
    },
    {
      title: "CONSENSUS",
      key: "consensus",
      width: 140,
      render: (_, record) => (
        <div className="flex items-center gap-2">
          <Progress
            percent={record.consensus}
            showInfo={false}
            size={["100%", 6]}
            strokeColor="#3E5EB9"
            className="flex-1"
          />
          <span className="text-sm text-[#606060] whitespace-nowrap">
            {record.consensus}%
          </span>
        </div>
      ),
    },
    {
      title: "STATUS",
      dataIndex: "status",
      key: "status",
      width: 160,
      render: (value, record) => (
        <StatusBadge status={value} total={record.awaiting_count} />
      ),
    },
    {
      title: "ACTIONS",
      key: "actions",
      width: 90,
      align: "right",
      render: (_, record) => (
        <Button
          type="link"
          className="edm-reviews-action"
          onClick={() => {
            router.push(`/validations/${id}/${record.administration_id}`);
          }}
        >
          {record.status === "validated" ? "View" : "Validate"}
        </Button>
      ),
    },
  ];

  return (
    <div className="w-full h-auto">
      {/* Full-width header */}
      <div className="relative left-1/2 w-screen -translate-x-1/2 -mt-3 bg-white pb-24 pt-16">
        <div
          aria-hidden
          className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
        />
        <div className="relative mx-auto w-full max-w-[1280px] flex flex-col gap-6">
          {publishedDate && (
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 text-sm leading-[21px] text-[#606060]">
                <CalendarOutlined />
                Published:
              </span>
              <span className="rounded border border-[#d2d2d2] px-2 py-0.5 text-sm leading-[21px] text-[#333333]">
                {publishedDate}
              </span>
            </div>
          )}
          <div className="flex w-full flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex flex-col gap-3">
              <h1 className="text-[34px] font-bold leading-10 text-[#333333]">
                This month drought validation
              </h1>
              <p className="text-base leading-6 text-[#606060]">
                Lorem ipsum dolor sit amet consectetur.
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <Button type="link" className="edm-reviews-action">
                Methodology
              </Button>
              <Button
                type="primary"
                disabled={!allValidated}
                onClick={() => setPublishOpen(true)}
              >
                Publish validated map
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />

        <Can I="read" a="Publication">
          {/* Summary cards */}
          <div className="relative z-10 mx-auto -mt-16 grid w-full max-w-[1280px] grid-cols-1 gap-0 sm:grid-cols-2 lg:grid-cols-4">
            {summary.data.map((card) => (
              <MetricCard
                key={card.key}
                label={card.label}
                value={card.value}
                delta={card.delta || null}
                deltaSuffix={card.delta_suffix || ""}
                sublabel={card.meta}
              />
            ))}
          </div>

          {/* Validation queue */}
          <section className="relative z-10 mx-auto mt-6 w-full max-w-[1280px] border border-[#eaecf0] bg-white">
            <div className="flex flex-col gap-4 border-b border-[#eaecf0] px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <h2 className="text-xl font-semibold leading-7 text-[#333333]">
                Validation queue
              </h2>
              <div className="flex items-center gap-3">
                <Input
                  placeholder="Search"
                  prefix={<SearchOutlined className="text-[#a4a4a4]" />}
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="w-48"
                  style={{ height: 40 }}
                  allowClear
                />
                <Button
                  disabled
                  style={{
                    height: 40,
                    backgroundColor: "#fff",
                    borderColor: "#d2d2d2",
                  }}
                >
                  Export CSV
                </Button>
              </div>
            </div>
            <div className="flex flex-col gap-4 border-b border-[#eaecf0] p-4 lg:flex-row lg:items-center lg:justify-between">
              <TabButtons
                options={STATUS_FILTERS}
                value={statusFilter}
                onChange={(value) => {
                  setStatusFilter(value);
                  setPage(1);
                }}
              />
            </div>
            <Table
              className="edm-reviews-table"
              columns={columns}
              dataSource={filteredData}
              rowKey="administration_id"
              loading={loading}
              tableLayout="fixed"
              scroll={{ x: 1000 }}
              pagination={
                filteredData.length <= PAGE_SIZE
                  ? false
                  : {
                      current: page,
                      pageSize: PAGE_SIZE,
                      total: filteredData.length,
                      responsive: true,
                      align: "center",
                      position: ["bottomCenter"],
                      onChange: (_page) => setPage(_page),
                    }
              }
            />
          </section>
        </Can>

        <div className="mx-auto w-full max-w-[1280px] py-8">
          <FeedbackSection />
        </div>
      </div>

      <PublishModal
        open={publishOpen}
        onCancel={() => setPublishOpen(false)}
        onPublish={(values) => {
          console.log("Publish:", values);
          setPublishOpen(false);
        }}
      />
    </div>
  );
};

export default ValidationDetailPage;
