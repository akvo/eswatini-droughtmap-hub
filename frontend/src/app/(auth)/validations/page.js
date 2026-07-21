"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, DatePicker, Table, Tag } from "antd";
import { CalendarOutlined } from "@ant-design/icons";
import { Can, FeedbackSection, TabButtons } from "@/components";
import { api } from "@/lib";
import { PAGE_SIZE } from "@/static/config";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";

dayjs.extend(advancedFormat);

const STATUS_FILTERS = [
  { label: "All", value: "all" },
  { label: "Not yet started", value: "not_yet_started" },
  { label: "Pending", value: "pending" },
  { label: "Completed", value: "completed" },
];

const PUBLICATION_STATUS_MAP = {
  1: { label: "Not yet started", color: "#667085" },
  2: { label: "Pending", color: "#f39c12" },
  3: { label: "Completed", color: "#12b76a" },
};

const { RangePicker } = DatePicker;

const ValidationsPage = () => {
  const [publications, setPublications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [totalData, setTotalData] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateRange, setDateRange] = useState(null);
  const router = useRouter();

  const columns = [
    {
      title: "DEADLINE",
      dataIndex: "due_date",
      key: "due_date",
      width: "26%",
      defaultSortOrder: "descend",
      sorter: (a, b) =>
        dayjs(a.due_date, "DD-MM-YYYY").unix() -
        dayjs(b.due_date, "DD-MM-YYYY").unix(),
      render: (value) =>
        value ? dayjs(value, "DD-MM-YYYY").format("DD/MM/YYYY") : "-",
    },
    {
      title: "MONTH",
      dataIndex: "year_month",
      key: "year_month",
      width: "26%",
      render: (value) =>
        value ? dayjs(value, "YYYY-MM").format("MMMM YYYY") : "-",
    },
    {
      title: "REVIEWS",
      dataIndex: "progress_reviews",
      key: "progress_reviews",
      width: "26%",
    },
    {
      title: "STATUS",
      dataIndex: "status",
      key: "status",
      width: "12%",
      render: (value) => {
        const statusInfo = PUBLICATION_STATUS_MAP[value] || {
          label: "Unknown",
          color: "#999",
        };
        return (
          <Tag className="edm-reviews-status-tag" color={statusInfo.color}>
            {statusInfo.label}
          </Tag>
        );
      },
    },
    {
      title: "ACTIONS",
      key: "actions",
      width: "10%",
      align: "right",
      render: (_, record) => (
        <Button
          type="link"
          className="edm-reviews-action"
          onClick={() => {
            router.push(`/validations/${record.id}`);
          }}
        >
          Validate
        </Button>
      ),
    },
  ];

  const queryString = useMemo(() => {
    const params = new URLSearchParams({ page });

    if (statusFilter !== "all") {
      params.set("status", statusFilter);
    }
    if (dateRange?.[0]) {
      params.set("start_date", dateRange[0].format("YYYY-MM-DD"));
    }
    if (dateRange?.[1]) {
      params.set("end_date", dateRange[1].format("YYYY-MM-DD"));
    }

    return params.toString();
  }, [dateRange, page, statusFilter]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const { data = [], total = 0 } = await api(
        "GET",
        `/admin/publications?${queryString}`,
      );
      setTotalData(total);
      setPublications(data.map((d) => ({ key: d?.id, ...d })));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [queryString]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const headerDate = useMemo(() => {
    const first = publications?.[0];
    if (first?.updated_at) {
      return dayjs(first.updated_at).format("D MMMM YYYY");
    }
    return null;
  }, [publications]);

  return (
    <div className="w-full h-auto">
      {/* Full-width header with fainted background pattern */}
      <div className="relative left-1/2 w-screen -translate-x-1/2 -mt-3 bg-white pb-24 pt-16">
        <div
          aria-hidden
          className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
        />
        <div className="relative mx-auto w-full max-w-[1280px] flex flex-col gap-6">
          {headerDate && (
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 text-sm leading-[21px] text-[#606060]">
                <CalendarOutlined />
                Last updated
              </span>
              <span className="rounded border border-[#d2d2d2] px-2 py-0.5 text-sm leading-[21px] text-[#333333]">
                {headerDate}
              </span>
            </div>
          )}
          <div className="flex flex-col gap-3">
            <h1 className="text-[34px] font-bold leading-10 text-[#333333]">
              My validations
            </h1>
            <p className="text-base leading-6 text-[#606060]">
              Lorem ipsum dolor sit amet consectetur.
            </p>
          </div>
        </div>
      </div>

      <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <Can I="read" a="Publication">
          <section className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px] border border-[#eaecf0] bg-white">
            <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6">
              <h2 className="text-xl font-semibold leading-7 text-[#333333]">
                Reviews
              </h2>
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
              <RangePicker
                className="edm-reviews-range-picker"
                format="D MMM YYYY"
                prefix={<CalendarOutlined style={{ marginRight: 8 }} />}
                suffixIcon={null}
                value={dateRange}
                onChange={(value) => {
                  setDateRange(value);
                  setPage(1);
                }}
              />
            </div>
            <Table
              className="edm-reviews-table"
              columns={columns}
              dataSource={publications}
              loading={loading}
              tableLayout="fixed"
              scroll={{ x: 900 }}
              pagination={
                totalData < PAGE_SIZE
                  ? false
                  : {
                      current: page,
                      pageSize: PAGE_SIZE,
                      total: totalData,
                      responsive: true,
                      align: "center",
                      position: ["bottomCenter"],
                      onChange: (_page) => {
                        setPage(_page);
                      },
                    }
              }
            />
          </section>
        </Can>
        <div className="mx-auto w-full max-w-[1280px] py-8">
          <FeedbackSection />
        </div>
      </div>
    </div>
  );
};

export default ValidationsPage;
