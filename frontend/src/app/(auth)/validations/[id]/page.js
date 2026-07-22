"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  useParams,
  usePathname,
  useRouter,
  useSearchParams,
} from "next/navigation";
import {
  Alert,
  Avatar,
  Button,
  Input,
  Progress,
  Table,
  Tag,
  Tooltip,
} from "antd";
import {
  CalendarOutlined,
  SearchOutlined,
  LeftOutlined,
} from "@ant-design/icons";
import { Can, FeedbackSection, TabButtons } from "@/components";
import { MetricCard } from "@/components/DS";
import { api } from "@/lib";
import {
  PAGE_SIZE,
  DROUGHT_CATEGORY_CODE,
  PUBLICATION_STATUS,
} from "@/static/config";
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

const SEARCH_DEBOUNCE_MS = 400;

const ValidationDetailPage = () => {
  const { id } = useParams();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  /**
   * Filters live in the URL, not in local state: the Validation Decision page
   * has to send the admin back to the same tab, search and page, and local
   * state does not survive navigating away.
   */
  const statusFilter = searchParams.get("status") || "all";
  const search = searchParams.get("search") || "";
  const page = Number(searchParams.get("page")) || 1;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [publishOpen, setPublishOpen] = useState(false);
  const [summary, setSummary] = useState(null);
  const [queue, setQueue] = useState({ data: [], total: 0 });
  const [searchDraft, setSearchDraft] = useState(search);

  const meta = summary?.meta;
  const cards = summary?.data || [];

  const setQuery = useCallback(
    (patch) => {
      const next = new URLSearchParams(searchParams.toString());
      Object.entries(patch).forEach(([key, value]) => {
        if (value === null || value === "" || value === "all") {
          next.delete(key);
        } else {
          next.set(key, String(value));
        }
      });
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const queryString = useMemo(() => {
    const params = new URLSearchParams({ page: String(page) });
    if (statusFilter !== "all") {
      params.set("status", statusFilter);
    }
    if (search) {
      params.set("search", search);
    }
    return params.toString();
  }, [page, search, statusFilter]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [stats, administrations] = await Promise.all([
        api("GET", `/admin/validation/${id}/stats`),
        api("GET", `/admin/validation/${id}/administrations?${queryString}`),
      ]);
      setSummary(stats);
      setQueue({
        data: administrations?.data || [],
        total: administrations?.total || 0,
      });
    } catch (err) {
      console.error(err);
      setError("Could not load the validation queue.");
    } finally {
      setLoading(false);
    }
  }, [id, queryString]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Debounce typing into ?search=, while staying in sync when the URL changes
  // underneath us — the back button, or a return from the decision page.
  const searchRef = useRef(search);
  useEffect(() => {
    if (searchRef.current !== search) {
      searchRef.current = search;
      setSearchDraft(search);
    }
  }, [search]);

  useEffect(() => {
    if (searchDraft === search) {
      return undefined;
    }
    const timer = setTimeout(() => {
      searchRef.current = searchDraft;
      setQuery({ search: searchDraft, page: 1 });
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [search, searchDraft, setQuery]);

  const decisionQuery = useMemo(() => {
    const params = new URLSearchParams();
    if (statusFilter !== "all") {
      params.set("status", statusFilter);
    }
    if (search) {
      params.set("search", search);
    }
    return params.toString();
  }, [search, statusFilter]);

  const publishedDate = meta?.published_at
    ? dayjs(meta.published_at).format("D MMMM YYYY")
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
      title: (
        <Tooltip title="Agreement between reviewers, weighted by how far apart their D-classes are. 100% = unanimous.">
          <span>CONSENSUS</span>
        </Tooltip>
      ),
      key: "consensus",
      width: 140,
      render: (_, record) => (
        <div className="flex items-center gap-2">
          <Progress
            percent={record.consensus ?? 0}
            showInfo={false}
            size={["100%", 6]}
            strokeColor="#3E5EB9"
            className="flex-1"
          />
          <span className="text-sm text-[#606060] whitespace-nowrap">
            {record.consensus === null ? "—" : `${record.consensus}%`}
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
            // Carry status + search so the decision page can resolve
            // Previous/Next and send the admin back to the same tab. `page`
            // is deliberately NOT carried — it is derived server-side and a
            // copy here goes stale as soon as Next crosses a page boundary.
            router.push(
              `/validations/${id}/${record.administration_id}${
                decisionQuery ? `?${decisionQuery}` : ""
              }`,
            );
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
                {meta?.year_month
                  ? `${dayjs(meta.year_month, "YYYY-MM").format("MMMM YYYY")} drought validation`
                  : "Drought validation"}
              </h1>
              <p className="text-base leading-6 text-[#606060]">
                Sign off the final drought class for every Inkhundla, then
                publish the validated map.
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <Button type="link" className="edm-reviews-action">
                Methodology
              </Button>
              <Tooltip
                title={
                  meta && !meta.can_publish
                    ? `${meta.pending_validation} Tinkhundla still need validation`
                    : ""
                }
              >
                <Button
                  type="primary"
                  disabled={!meta?.can_publish}
                  onClick={() => setPublishOpen(true)}
                >
                  Publish validated map
                </Button>
              </Tooltip>
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
            {cards.map((card) => (
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
                  value={searchDraft}
                  onChange={(e) => setSearchDraft(e.target.value)}
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
                onChange={(value) => setQuery({ status: value, page: 1 })}
              />
            </div>
            {error && (
              <Alert
                type="error"
                message={error}
                showIcon
                className="m-4"
                action={
                  <Button size="small" onClick={fetchData}>
                    Retry
                  </Button>
                }
              />
            )}
            <Table
              className="edm-reviews-table"
              columns={columns}
              dataSource={queue.data}
              rowKey="administration_id"
              loading={loading}
              tableLayout="fixed"
              scroll={{ x: 1000 }}
              pagination={{
                current: page,
                pageSize: PAGE_SIZE,
                total: queue.total,
                responsive: true,
                align: "center",
                position: ["bottomCenter"],
                hideOnSinglePage: true,
                showSizeChanger: false,
                onChange: (_page) => setQuery({ page: _page }),
              }}
            />
          </section>
        </Can>

        <div className="mx-auto w-full max-w-[1280px] py-8">
          <FeedbackSection />
        </div>
      </div>

      <PublishModal
        open={publishOpen}
        yearMonth={meta?.year_month}
        onCancel={() => setPublishOpen(false)}
        onPublish={async ({ narrative }) => {
          // api() resolves on 4xx rather than rejecting, so a failed publish
          // has to be detected from the body — never from a catch block.
          const res = await api("PUT", `/admin/publication/${id}`, {
            status: PUBLICATION_STATUS.published,
            narrative,
          });
          if (res?.status !== PUBLICATION_STATUS.published) {
            return res?.status?.[0] ?? "Publish failed.";
          }
          setPublishOpen(false);
          fetchData();
          return null;
        }}
      />
    </div>
  );
};

export default ValidationDetailPage;
