"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Table, Tag } from "antd";
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

const ReviewsPage = () => {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [totalData, setTotalData] = useState(0);
  const [page, setPage] = useState(1);
  const [preload, setPreload] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const router = useRouter();

  const columns = [
    {
      title: "DEADLINE",
      dataIndex: "due_date",
      key: "due_date",
      defaultSortOrder: "descend",
      sorter: (a, b) => new Date(a.due_date) - new Date(b.due_date),
      render: (value) => dayjs(value, "YYYY-MM-DD").format("MMMM Do, YYYY"),
    },
    {
      title: "MONTH",
      dataIndex: "year_month",
      key: "year_month",
      render: (value) => dayjs(value, "YYYY-MM").format("MMMM YYYY"),
    },
    {
      title: "TINKHUNDLA",
      dataIndex: "progress_review",
      key: "progress_review",
    },
    {
      title: "STATUS",
      dataIndex: "is_completed",
      key: "is_completed",
      render: (_, { is_completed }) => (
        <Tag color={is_completed ? "success" : "#6b7280"}>
          {is_completed ? "Completed" : "Pending"}
        </Tag>
      ),
    },
  ];

  const fetchData = useCallback(async () => {
    try {
      if (preload) {
        setPreload(false);
        setLoading(true);
        const { data, total } = await api(
          "GET",
          `/reviewer/reviews?page=${page}`,
        );
        setTotalData(total);
        const _reviews = data.map((d) => ({ key: d?.id, ...d }));
        setReviews(_reviews);
        setLoading(false);
      }
    } catch (err) {
      console.error(err);
      setPreload(false);
    }
  }, [preload, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ponytail: client-side filter on the loaded page — fine while reviews fit
  // one page; move to a server `status` param when the API supports it.
  const filteredReviews = useMemo(
    () =>
      reviews.filter((r) =>
        statusFilter === "all"
          ? true
          : statusFilter === "completed"
            ? r.is_completed
            : !r.is_completed,
      ),
    [reviews, statusFilter],
  );

  return (
    <div className="w-full h-auto space-y-6 pt-6">
      <PageHeader
        title="My reviews"
        description="Review and validate the CDI drought maps assigned to you."
      />
      <Can I="read" a="Review">
        <div className="space-y-4">
          <TabButtons
            options={STATUS_FILTERS}
            value={statusFilter}
            onChange={setStatusFilter}
          />
          <Table
            columns={columns}
            dataSource={filteredReviews}
            loading={loading}
            onRow={(record) => {
              return {
                onClick: () => {
                  router.push(`/reviews/${record.id}`);
                },
              };
            }}
            rowClassName={"cursor-pointer"}
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
                      setPreload(true);
                    },
                  }
            }
          />
        </div>
      </Can>
      <div className="py-8">
        <FeedbackSection />
      </div>
    </div>
  );
};

export default ReviewsPage;
