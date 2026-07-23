"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Modal, Select, Table, Tag } from "antd";
import { FileOutlined } from "@ant-design/icons";
import { Can, FeedbackSection, PageHeader, TabButtons } from "@/components";
import {
  MAP_CATEGORY_OPTIONS,
  PAGE_SIZE,
  PUBLICATION_DISPLAY_STATUS,
  PUBLICATION_STATUS,
  PUBLICATION_TAB_FILTERS,
} from "@/static/config";
import { api } from "@/lib";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";

dayjs.extend(advancedFormat);

const SHOW_GEONODE_LINK = false;

const PublicationsPage = () => {
  const [publications, setPublications] = useState([]);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [preload, setPreload] = useState(true);
  const [totalData, setTotalData] = useState(0);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState(MAP_CATEGORY_OPTIONS[0].value);
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortField, setSortField] = useState("year_month");
  const [sortOrder, setSortOrder] = useState("descend");
  const router = useRouter();

  const columns = [
    {
      title: "CREATED AT",
      dataIndex: "created",
      key: "created",
      width: "15%",
      sorter: true,
      render: (_, { created }) =>
        created ? dayjs(created).format("DD/MM/YY") : "-",
    },
    {
      title: "PREVIEW",
      key: "preview",
      width: "35%",
      render: (_, record) => {
        const titleText = record?.title || "";
        const formattedTitle =
          titleText.length > 100 ? `${titleText.slice(0, 75)}.....` : titleText;
        return (
          <a
            role="button"
            onClick={() => setPreview(record)}
            className="flex gap-3 items-center cursor-pointer w-full"
          >
            <div className="bg-[#eceff8] rounded-full w-10 h-10 flex items-center justify-center shrink-0">
              <FileOutlined style={{ fontSize: 18, color: "#3e5eb9" }} />
            </div>
            <div className="flex flex-col min-w-0">
              <span
                className="text-sm font-medium text-[#333] leading-5"
                title={titleText}
              >
                {formattedTitle}
              </span>
              {record?.file_size && (
                <span className="text-sm text-[#606060] leading-5">
                  {record.file_size}
                </span>
              )}
            </div>
          </a>
        );
      },
    },
    {
      title: "PUBLICATION DATE",
      dataIndex: "year_month",
      key: "year_month",
      width: "18%",
      sorter: true,
      render: (_, { year_month }) =>
        year_month ? dayjs(year_month).format("MMMM YYYY") : "-",
    },
    {
      title: "STATUS",
      dataIndex: "status",
      key: "status",
      width: "12%",
      render: (_, { status }) => {
        const displayStatus = PUBLICATION_DISPLAY_STATUS[
          String(status ?? null)
        ] || {
          label: "Unknown",
          color: "#999",
        };
        return (
          <Tag className="edm-reviews-status-tag" color={displayStatus.color}>
            {displayStatus.label}
          </Tag>
        );
      },
    },
    {
      title: "ACTIONS",
      key: "actions",
      width: "20%",
      align: "right",
      render: (_, record) => {
        const { pk, publication_id, detail_url, status } = record;
        const isInValidation = status === PUBLICATION_STATUS.in_validation;
        const routeURL = publication_id
          ? isInValidation
            ? `/validations/${publication_id}`
            : `/publications/${publication_id}`
          : `/publications/create?cdi_geonode_id=${pk}`;

        const actionLabel = publication_id
          ? "Validate"
          : "Start new publication";

        return (
          <div className="flex gap-3 justify-end items-center">
            {SHOW_GEONODE_LINK && (
              <Button
                type="link"
                href={detail_url}
                target="_blank"
                className="edm-reviews-action"
              >
                Open in Geonode
              </Button>
            )}
            <Button
              type="link"
              className="edm-reviews-action"
              onClick={(e) => {
                e.stopPropagation();
                router.push(routeURL);
              }}
            >
              {actionLabel}
            </Button>
          </div>
        );
      },
    },
  ];

  const handleTableChange = (pagination, filters, sorter) => {
    if (sorter && sorter.field) {
      setSortField(sorter.field);
      setSortOrder(sorter.order);
      setPreload(true);
    }
  };

  const fetchData = useCallback(async () => {
    try {
      if (preload) {
        setLoading(true);
        setPreload(false);
        const sort_order =
          sortOrder === "descend"
            ? "desc"
            : sortOrder === "ascend"
              ? "asc"
              : "desc";

        const params = new URLSearchParams({
          page,
          category,
          sort: sortField,
          sort_order,
        });

        if (statusFilter !== "all") {
          params.set("status", statusFilter);
        }

        const { data, total } = await api(
          "GET",
          `/admin/cdi-geonode?${params.toString()}`,
        );

        if (total !== undefined) {
          setTotalData(total);
        }
        if (data) {
          const _publications = data.map((d) => ({ key: d?.pk, ...d }));
          setPublications(_publications);
        }
        setLoading(false);
      }
    } catch (err) {
      console.error(err);
      setLoading(false);
      setPreload(false);
    }
  }, [preload, page, statusFilter, category, sortField, sortOrder]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const headerDate = useMemo(() => {
    const first = publications?.[0];
    if (first?.created) {
      return dayjs(first.created).format("D MMMM YYYY");
    }
    return null;
  }, [publications]);

  return (
    <div className="w-full h-auto">
      <PageHeader
        title="CDI publication"
        description="Manage and track CDI map publications."
        date={headerDate}
      />

      <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <Can I="read" a="Publication">
          <section className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px] border border-[#eaecf0] bg-white">
            <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6">
              <h2 className="text-xl font-semibold leading-7 text-[#333333]">
                Reviews
              </h2>
            </div>
            <div className="flex flex-col gap-4 border-b border-[#eaecf0] p-4 lg:flex-row lg:items-center lg:justify-between">
              <TabButtons
                options={PUBLICATION_TAB_FILTERS}
                value={statusFilter}
                onChange={(value) => {
                  setStatusFilter(value);
                  setPage(1);
                  setPreload(true);
                }}
              />
              <Select
                options={MAP_CATEGORY_OPTIONS}
                className="w-full lg:w-48"
                placeholder="Filter by Category"
                onChange={(value) => {
                  setPage(1);
                  if (value) {
                    setCategory(value);
                  } else {
                    setCategory(MAP_CATEGORY_OPTIONS[0].value);
                  }
                  setPreload(true);
                }}
                value={category}
                allowClear={false}
              />
            </div>
            <Table
              className="edm-reviews-table"
              columns={columns}
              dataSource={publications}
              loading={loading}
              tableLayout="fixed"
              scroll={{ x: 900 }}
              onChange={handleTableChange}
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
                      showSizeChanger: false,
                      onChange: (_page) => {
                        setPage(_page);
                        setPreload(true);
                      },
                    }
              }
              rowKey="pk"
            />
          </section>
        </Can>
        <div className="mx-auto w-full max-w-[1280px] py-8">
          <FeedbackSection />
        </div>
      </div>

      <Modal
        title={preview?.title}
        open={!!preview?.pk}
        onOk={() => {
          setPreview(null);
        }}
        onCancel={() => {
          setPreview(null);
        }}
        cancelButtonProps={{ style: { display: "none" } }}
        width={800}
        className="w-full flex flex-col items-center"
        closable
      >
        {preview?.embed_url ? (
          <iframe
            width={"100%"}
            height={600}
            src={preview.embed_url}
            className="min-w-[640px]"
          />
        ) : (
          <p className="py-8 text-center text-gray-500">No preview available</p>
        )}
      </Modal>
    </div>
  );
};

export default PublicationsPage;
