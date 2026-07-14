import React, { useState, useEffect } from "react";
import { Select, Input, Button } from "antd";
import TabButtons from "@/components/TabButtons";
import { ACTIVITY_SECTOR_OPTIONS } from "@/static/config";

const STATUS_FILTERS = [
  { label: "All", value: "all" },
  { label: "Active", value: 2 },
  { label: "Draft", value: 1 },
  { label: "Archived", value: 3 },
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
    const timer = setTimeout(() => {
      onSearchChange(searchVal);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchVal, onSearchChange]);

  return (
    <>
      {/* Title + search + export row */}
      <div className="flex flex-col gap-4 border-b border-[#eaecf0] px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
        <h2 className="m-0 text-xl font-semibold leading-7 text-[#333333]">
          Operation procedures
        </h2>
        <div className="flex w-full items-center gap-3 lg:w-auto">
          <Input.Search
            placeholder="Search"
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
      <div className="flex flex-col gap-4 border-b border-[#eaecf0] p-4 lg:flex-row lg:items-center lg:justify-between">
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
