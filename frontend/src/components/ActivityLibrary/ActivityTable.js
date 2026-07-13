import React from "react";
import { Table, Tag, Button } from "antd";
import ActivityStatusTag from "./ActivityStatusTag";

const SECTOR_TAG_COLORS = {
  1: "green",
  2: "red",
  3: "blue",
  4: "gold",
  5: "cyan",
  6: "purple",
  7: "orange",
  8: "geekblue",
};

export default function ActivityTable({
  activities = [],
  loading = false,
  page = 1,
  total = 0,
  onPageChange,
}) {
  const columns = [
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (status) => <ActivityStatusTag status={status} />,
    },
    {
      title: "Protocol ID",
      dataIndex: "code",
      key: "code",
      className: "font-semibold text-neutral-800",
    },
    {
      title: "Title",
      dataIndex: "title",
      key: "title",
      className: "text-neutral-700",
    },
    {
      title: "Sector",
      dataIndex: "sector",
      key: "sector",
      render: (sector, record) => (
        <Tag color={SECTOR_TAG_COLORS[sector] || "default"}>
          {record.sector_label}
        </Tag>
      ),
    },
    {
      title: "Owner",
      dataIndex: "owner",
      key: "owner",
      render: (owner) => owner || "-",
    },
    {
      title: "Version",
      dataIndex: "version",
      key: "version",
    },
    {
      title: "Last reviewed",
      dataIndex: "updated_at",
      key: "updated_at",
      render: (dateStr) => {
        if (!dateStr) return "-";
        const date = new Date(dateStr);
        const day = String(date.getDate()).padStart(2, "0");
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const year = date.getFullYear();
        return `${day}/${month}/${year}`;
      },
    },
    {
      title: "Actions",
      key: "actions",
      render: () => (
        <Button type="link" size="small" className="p-0">
          View
        </Button>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={activities.map((a) => ({ ...a, key: a.id }))}
      loading={loading}
      pagination={{
        current: page,
        total: total,
        pageSize: 10,
        onChange: onPageChange,
        showSizeChanger: false,
      }}
      className="border border-neutral-200 overflow-hidden bg-white shadow-sm"
    />
  );
}
