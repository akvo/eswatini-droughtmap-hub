import React, { useState, useEffect } from "react";
import { Radio, Select, Input, Button } from "antd";
import { ACTIVITY_SECTOR_OPTIONS } from "@/static/config";

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
  }, [searchVal]);

  return (
    <div className="bg-white p-4 border border-neutral-200">
      {/* Title + Action controls row */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
        <h3 className="text-base font-bold text-neutral-800 m-0">
          Operation procedures
        </h3>
        <div className="flex w-full md:w-auto items-center gap-3">
          <Input.Search
            placeholder="Search by title or code..."
            value={searchVal}
            onChange={(e) => setSearchVal(e.target.value)}
            className="w-full md:w-64"
            allowClear
          />
          <Button onClick={onExport} type="default">
            Export CSV
          </Button>
        </div>
      </div>

      {/* Filter controls row */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-neutral-100 pt-4">
        <Radio.Group
          value={statusFilter}
          onChange={(e) => onStatusChange(e.target.value)}
          buttonStyle="solid"
        >
          <Radio.Button value="all">All</Radio.Button>
          <Radio.Button value={2}>Active</Radio.Button>
          <Radio.Button value={1}>Draft</Radio.Button>
          <Radio.Button value={3}>Archived</Radio.Button>
        </Radio.Group>

        <Select
          value={sectorFilter}
          onChange={onSectorChange}
          className="w-full md:w-48"
          options={ACTIVITY_SECTOR_OPTIONS}
        />
      </div>
    </div>
  );
}
