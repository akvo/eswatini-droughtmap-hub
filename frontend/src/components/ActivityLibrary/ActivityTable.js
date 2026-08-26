import React from "react";
import { Table, Button } from "antd";
import ActivityStatusTag from "./ActivityStatusTag";
import { SectorBadge } from "@/components/DS";

export default function ActivityTable({
  activities = [],
  loading = false,
  page = 1,
  total = 0,
  onPageChange,
  onRowClick,
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
        <SectorBadge sector={sector} label={record.sector_label} />
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
      align: "right",
      render: (_, record) => (
        <Button
          type="link"
          className="edm-reviews-action"
          onClick={(e) => {
            e.stopPropagation();
            if (onRowClick) onRowClick(record);
          }}
        >
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
      scroll={{ x: 900 }}
      pagination={{
        current: page,
        total: total,
        pageSize: 10,
        onChange: onPageChange,
        showSizeChanger: false,
        responsive: true,
        align: "center",
        position: ["bottomCenter"],
      }}
      className="edm-reviews-table"
      onRow={(record) => ({
        onClick: () => {
          if (onRowClick) onRowClick(record);
        },
        style: { cursor: "pointer" },
      })}
    />
  );
}
