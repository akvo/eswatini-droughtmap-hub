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
  Checkbox,
  Input,
  Modal,
  Progress,
  Table,
  Tag,
  Tooltip,
  message,
} from "antd";
import {
  CalendarOutlined,
  SearchOutlined,
  LeftOutlined,
} from "@ant-design/icons";
import { Can, FeedbackSection, TabButtons } from "@/components";
import { DroughtScore, MetricCard } from "@/components/DS";
import { api } from "@/lib";
import {
  MIN_TWGS_PER_PUBLICATION,
  PAGE_SIZE,
  PUBLICATION_STATUS,
} from "@/static/config";
import dayjs from "dayjs";
import { PublishModal, ReviewerPanelModal } from "@/components/Validation";

/**
 * First message out of a DRF error body, whichever field it came from.
 * Reading only `status` was enough while the publish payload carried one
 * validatable field; with `bulletin_url` alongside it, a mistyped URL would
 * otherwise surface as the generic "Publish failed." with the real reason
 * ("Enter a valid URL.") dropped on the floor.
 */
const firstError = (res) =>
  Object.values(res || {})
    .flat()
    .find((value) => typeof value === "string") ?? "Publish failed.";

const STATUS_FILTERS = [
  { label: "All", value: "all" },
  { label: "Ready", value: "ready" },
  { label: "Awaiting review", value: "awaiting" },
  { label: "Validated", value: "validated" },
];

/**
 * Mirrors backend AgreementFilter. Cross-cuts the status tabs rather than
 * extending them: the tabs are a partition whose counts must keep summing to
 * the total, and agreement is orthogonal to all three (design D-6).
 */
const AGREEMENT = {
  undisputed: "undisputed",
  disagreement: "disagreement",
};

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

/**
 * The D-classes the reviewers submitted. Hue and copy come from
 * DROUGHT_CATEGORY_* in config.js via DroughtScore, so these chips can never
 * disagree with the map, the legend or the decision page.
 */
const DClassSpread = ({ levels = [] }) => (
  <div className="flex items-center gap-1">
    {levels.map((level, i) => (
      <DroughtScore key={i} level={level} size="sm" />
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
  const agreement = searchParams.get("agreement") || "";
  const page = Number(searchParams.get("page")) || 1;
  const nonDisputedOnly = agreement === AGREEMENT.undisputed;

  const [loading, setLoading] = useState(false);
  const [bulkRunning, setBulkRunning] = useState(false);
  const [error, setError] = useState(null);
  const [publishOpen, setPublishOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
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
    if (agreement) {
      params.set("agreement", agreement);
    }
    return params.toString();
  }, [agreement, page, search, statusFilter]);

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
    // Carried too, or Previous/Next would walk the unfiltered queue and the
    // admin would land on rows the filter had just excluded (AC-3.1).
    if (agreement) {
      params.set("agreement", agreement);
    }
    return params.toString();
  }, [agreement, search, statusFilter]);

  /**
   * The bulk action is scoped to the filter, never to a selection (D-3). The
   * server re-derives the set at write time and re-applies status=ready
   * whatever we send, so a stale count here can only ever write less than it
   * promised — never more.
   */
  const runBulkValidation = useCallback(() => {
    Modal.confirm({
      title: "Validate all non-disputed Tinkhundla?",
      content: (
        <span>
          <strong>{queue.total}</strong>{" "}
          {queue.total === 1 ? "Inkhundla has" : "Tinkhundla have"} the same
          D-class from every reviewer. Each will be validated at that class and
          recorded against your name.
        </span>
      ),
      okText: "Validate all",
      onOk: async () => {
        setBulkRunning(true);
        try {
          // api() resolves on 4xx, so a refusal arrives as a body — it must be
          // detected from the payload, not from a catch block.
          const res = await api("POST", `/admin/validation/${id}/bulk`, {
            search,
          });
          if (typeof res?.validated !== "number") {
            message.error("Bulk validation failed.");
            return;
          }
          message.success(res.message);
          fetchData();
        } finally {
          setBulkRunning(false);
        }
      },
    });
  }, [fetchData, id, queue.total, search]);

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
      width: 200,
      render: (value, record) => (
        <div className="flex items-center gap-2">
          <StatusBadge status={value} total={record.awaiting_count} />
          {/* The final class the admin assigned. The D-CLASS SPREAD column
              shows what the reviewers submitted; without this the outcome of
              a validated row is invisible until you open it. */}
          {record.validated_category !== null &&
            record.validated_category !== undefined && (
              <Tooltip title="Final validated D-class">
                <span>
                  <DroughtScore level={record.validated_category} size="sm" />
                </span>
              </Tooltip>
            )}
        </div>
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
          disabled={record.reviews_completed === 0}
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
              {/* <Button
                className="edm-reviews-action"
                onClick={() => setPanelOpen(true)}
              >
                Reviewer panel
              </Button> */}
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
                  {publishedDate
                    ? "Update published map"
                    : "Publish validated map"}
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
                // Only the disagreement card drills through. The other three
                // mirror the status tabs, which are already one click away —
                // and this card had no way in at all until now.
                active={
                  card.key === AGREEMENT.disagreement &&
                  agreement === AGREEMENT.disagreement
                }
                onClick={
                  card.key === AGREEMENT.disagreement
                    ? () =>
                        // Toggles. Applying a filter with no way back out of
                        // it strands the admin on a subset of the queue with
                        // nothing on screen admitting why.
                        setQuery({
                          agreement:
                            agreement === AGREEMENT.disagreement
                              ? null
                              : AGREEMENT.disagreement,
                          status: "all",
                          page: 1,
                        })
                    : null
                }
              />
            ))}
          </div>

          {/* A single Technical Working Group makes every Inkhundla "ready"
              off one institution's response, so the queue looks finished when
              nothing has been cross-checked. Sits BELOW the cards: they carry
              `-mt-16` to overlap the hero, so anything above them is drawn
              underneath and clipped. */}
          {meta && meta.reviewers_required < MIN_TWGS_PER_PUBLICATION && (
            // The centring lives on a plain div, not on the Alert: antd 5
            // injects its component CSS at runtime, after Tailwind's sheet, so
            // `mx-auto` on `.ant-alert` itself is not dependable.
            <div className="relative z-10 mx-auto mt-6 w-full max-w-[1280px]">
              <Alert
                type="warning"
                showIcon
                message="This publication has only one Technical Working Group reviewing it."
                description="Every Inkhundla counts as fully reviewed after that one response, so no row can show consensus or be bulk-validated. Add reviewers from another working group to cross-check."
                action={
                  <Button size="small" onClick={() => setPanelOpen(true)}>
                    Reviewer panel
                  </Button>
                }
              />
            </div>
          )}

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
                onChange={(value) =>
                  // Picking a tab clears the agreement filter: leaving it on
                  // would silently intersect two filters while only one of
                  // them looks active.
                  setQuery({ status: value, agreement: null, page: 1 })
                }
              />
              <div className="flex items-center gap-4">
                <Checkbox
                  checked={nonDisputedOnly}
                  onChange={(e) =>
                    // Sets the Ready tab too, so what the admin sees is
                    // exactly what "Validate all N" will write (D-3).
                    setQuery(
                      e.target.checked
                        ? {
                            agreement: AGREEMENT.undisputed,
                            status: "ready",
                            page: 1,
                          }
                        : { agreement: null, page: 1 },
                    )
                  }
                >
                  Non-disputed only
                </Checkbox>
                {nonDisputedOnly && (
                  <Button
                    type="primary"
                    disabled={!queue.total}
                    loading={bulkRunning}
                    onClick={runBulkValidation}
                  >
                    Validate all {queue.total} non-disputed
                  </Button>
                )}
              </div>
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

      <ReviewerPanelModal
        open={panelOpen}
        publicationId={id}
        onClose={() => setPanelOpen(false)}
        // Adding a reviewer changes reviewers_required, which moves rows
        // between Ready and Awaiting — refetch so the queue is not stale.
        onChanged={fetchData}
      />

      <PublishModal
        open={publishOpen}
        yearMonth={meta?.year_month}
        currentNarrative={meta?.narrative}
        currentBulletinUrl={meta?.bulletin_url}
        published={!!publishedDate}
        onCancel={() => setPublishOpen(false)}
        onPublish={async ({ narrative, bulletinUrl }) => {
          // api() resolves on 4xx rather than rejecting, so a failed publish
          // has to be detected from the body — never from a catch block.
          const res = await api("PUT", `/admin/publication/${id}`, {
            status: PUBLICATION_STATUS.published,
            narrative,
            bulletin_url: bulletinUrl,
          });
          if (res?.status !== PUBLICATION_STATUS.published) {
            return firstError(res);
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
