import React, { useState, useEffect } from "react";
import { Radio, Select, Input, Button } from "antd";

const SECTORS = [
  { value: "all", label: "All Sectors" },
  { value: 1, label: "Food & Agriculture" },
  { value: 2, label: "Health & Nutrition" },
  { value: 3, label: "Water & Sanitation" },
  { value: 4, label: "Education" },
  { value: 5, label: "Environment & Energy" },
  { value: 6, label: "Coordination" },
  { value: 7, label: "Social Protection" },
  { value: 8, label: "Transport & Logistics" },
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
  }, [searchVal]);

  return (
    <div className="bg-white p-4 border border-neutral-200 rounded-lg mb-6 shadow-sm">
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
          options={SECTORS}
        />
      </div>
    </div>
  );
}
