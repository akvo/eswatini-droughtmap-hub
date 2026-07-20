"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, DatePicker, Table, Tag } from "antd";
import { CalendarOutlined } from "@ant-design/icons";
import { Can, FeedbackSection, PageHeader, TabButtons } from "@/components";
import { api } from "@/lib";
import { PAGE_SIZE } from "@/static/config";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";

dayjs.extend(advancedFormat);

const STATUS_FILTERS = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending" },
  { label: "Completed", value: "completed" },
];

const { RangePicker } = DatePicker;

const ReviewsPage = () => {
  const [reviews, setReviews] = useState([]);
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
      sorter: (a, b) => new Date(a.due_date) - new Date(b.due_date),
      render: (value) =>
        value ? dayjs(value, "YYYY-MM-DD").format("DD/MM/YYYY") : "-",
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
      dataIndex: "progress_review",
      key: "progress_review",
      width: "26%",
    },
    {
      title: "STATUS",
      dataIndex: "is_completed",
      key: "is_completed",
      width: "12%",
      render: (_, { is_completed }) => (
        <Tag
          className="edm-reviews-status-tag"
          color={is_completed ? "#12b76a" : "#f39c12"}
        >
          {is_completed ? "Completed" : "Pending"}
        </Tag>
      ),
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
            router.push(`/reviews/${record.id}`);
          }}
        >
          Review
        </Button>
      ),
    },
  ];

  const reviewQuery = useMemo(() => {
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
        `/reviewer/reviews?${reviewQuery}`,
      );
      setTotalData(total);
      const _reviews = data.map((d) => ({ key: d?.id, ...d }));
      setReviews(_reviews);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [reviewQuery]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const headerDate = useMemo(() => {
    const firstReview = reviews?.[0];
    if (firstReview?.last_updated) {
      return dayjs(firstReview.last_updated).format("D MMMM YYYY");
    }
    return null;
  }, [reviews]);

  return (
    <div className="w-full h-auto">
      <PageHeader
        title="My reviews"
        description="Review and validate the CDI drought maps assigned to you."
        date={headerDate}
      />
      <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <Can I="read" a="Review">
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
              dataSource={reviews}
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

export default ReviewsPage;
