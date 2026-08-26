import React, { useState, useEffect } from "react";
import { Select, Input, Button } from "antd";
import TabButtons from "@/components/TabButtons";
import { ACTIVITY_SECTOR_OPTIONS, ACTIVITY_STATUS } from "@/static/config";

const STATUS_FILTERS = [
  { label: "All", value: "all" },
  { label: "Active", value: ACTIVITY_STATUS.active },
  { label: "Draft", value: ACTIVITY_STATUS.draft },
  { label: "Archived", value: ACTIVITY_STATUS.archived },
];

export default function ActivityTableFilters({
  statusFilter = "all",
  sectorFilter = "all",
  searchQuery = "",
  onStatusChange,
  onSectorChange,
  onSearchChange,
  onExport,
}) {
  const [searchVal, setSearchVal] = useState(searchQuery);

  useEffect(() => {
    if (searchVal === searchQuery) return;
    const timer = setTimeout(() => {
      onSearchChange(searchVal);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchVal, searchQuery, onSearchChange]);

  return (
    <>
      {/* Title + search + export row */}
      <div className="flex flex-col gap-4 border-b border-cardBorder px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
        <h2 className="m-0 text-xl font-semibold leading-7 text-textBody">
          Operation procedures
        </h2>
        <div className="flex w-full items-center gap-3 lg:w-auto">
          <Input.Search
            placeholder="Search by title or code..."
            value={searchVal}
            onChange={(e) => setSearchVal(e.target.value)}
            className="w-full lg:w-80"
            allowClear
          />
          <Button onClick={onExport} type="default">
            Export CSV
          </Button>
        </div>
      </div>

      {/* Filter controls row */}
      <div className="flex flex-col gap-4 border-b border-cardBorder p-4 lg:flex-row lg:items-center lg:justify-between">
        <TabButtons
          options={STATUS_FILTERS}
          value={statusFilter}
          onChange={onStatusChange}
        />
        <Select
          value={sectorFilter}
          onChange={onSectorChange}
          className="w-full lg:w-48"
          options={ACTIVITY_SECTOR_OPTIONS}
        />
      </div>
    </>
  );
}
