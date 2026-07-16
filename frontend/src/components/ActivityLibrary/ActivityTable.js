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

const SECTOR_ICONS = {
  1: (
    <svg
      className="w-3.5 h-3.5 inline mr-1 -mt-0.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.5 1 9.8a7 7 0 0 1-9 8.2Z"></path>
      <path d="M9 22v-4H7a3 3 0 0 1-3-3V9"></path>
    </svg>
  ),
  2: (
    <svg
      className="w-3.5 h-3.5 inline mr-1 -mt-0.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path>
    </svg>
  ),
  3: (
    <svg
      className="w-3.5 h-3.5 inline mr-1 -mt-0.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 22a7 7 0 0 0 7-7c0-4.3-7-11-7-11S5 10.7 5 15a7 7 0 0 0 7 7z"></path>
    </svg>
  ),
  4: (
    <svg
      className="w-3.5 h-3.5 inline mr-1 -mt-0.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"></path>
      <path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"></path>
    </svg>
  ),
  5: (
    <svg
      className="w-3.5 h-3.5 inline mr-1 -mt-0.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="4"></circle>
      <path d="M12 2v2"></path>
      <path d="M12 20v2"></path>
      <path d="M4.93 4.93l1.41 1.41"></path>
      <path d="M17.66 17.66l1.41 1.41"></path>
      <path d="M2 12h2"></path>
      <path d="M20 12h2"></path>
      <path d="M6.34 17.66l-1.41 1.41"></path>
      <path d="M19.07 4.93l-1.41 1.41"></path>
    </svg>
  ),
  6: (
    <svg
      className="w-3.5 h-3.5 inline mr-1 -mt-0.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
      <circle cx="9" cy="7" r="4"></circle>
      <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
      <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
    </svg>
  ),
  7: (
    <svg
      className="w-3.5 h-3.5 inline mr-1 -mt-0.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
    </svg>
  ),
  8: (
    <svg
      className="w-3.5 h-3.5 inline mr-1 -mt-0.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="1" y="3" width="15" height="13"></rect>
      <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon>
      <circle cx="5.5" cy="18.5" r="2.5"></circle>
      <circle cx="18.5" cy="18.5" r="2.5"></circle>
    </svg>
  ),
};

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
        <Tag color={SECTOR_TAG_COLORS[sector] || "default"}>
          {SECTOR_ICONS[sector]}
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
