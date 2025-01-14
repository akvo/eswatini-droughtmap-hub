"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Table, Tag, Typography } from "antd";
import { Can } from "@/components";
import { api } from "@/lib";
import { PAGE_SIZE } from "@/static/config";

const { Title } = Typography;

const ReviewsPage = () => {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalData, setTotalData] = useState(0);
  const router = useRouter();

  const columns = [
    {
      title: "DEADLINE",
      dataIndex: "due_date",
      key: "due_date",
      defaultSortOrder: "ascend",
      sorter: (a, b) => new Date(a.due_date) - new Date(b.due_date),
    },
    {
      title: "MONTH",
      dataIndex: "year_month",
      key: "year_month",
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
    const { data, total } = await api("GET", "/reviewer/reviews");
    setTotalData(total);
    const _reviews = data.map((d) => ({ key: d?.id, ...d }));
    setReviews(_reviews);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="w-full h-auto space-y-4">
      <Title level={2}>My reviews</Title>
      <Can I="read" a="Review">
        <Table
          columns={columns}
          dataSource={reviews}
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
                  pageSize: PAGE_SIZE,
                  total: totalData,
                  responsive: true,
                  align: "center",
                  position: ["bottomCenter"],
                }
          }
        />
      </Can>
    </div>
  );
};

export default ReviewsPage;
