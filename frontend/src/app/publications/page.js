"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  Button,
  Flex,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { Can } from "@/components";
import {
  PAGE_SIZE,
  PUBLICATION_STATUS,
  PUBLICATION_STATUS_OPTIONS,
} from "@/static/config";
import { api } from "@/lib";
import dayjs from "dayjs";

const { Title } = Typography;

const PublicationsPage = () => {
  const [publications, setPublications] = useState([]);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [totalData, setTotalData] = useState(0);
  const router = useRouter();

  const columns = [
    {
      title: "CREATED AT",
      dataIndex: "created",
      key: "created",
      defaultSortOrder: "descend",
      sorter: (a, b) => new Date(a.created) - new Date(b.created),
      render: (_, { created }) => dayjs(created).format("DD/MM/YYYY h:mm A"),
    },
    {
      title: "PREVIEW",
      dataIndex: "thumbnail_url",
      key: "thumbnail_url",
      render: (_, record) => {
        return (
          <a role="button" onClick={() => setPreview(record)}>
            <Image
              width={100}
              height={100}
              src={record?.thumbnail_url}
              alt={record?.title}
            />
            <small>{record?.title}</small>
          </a>
        );
      },
    },
    {
      title: "MONTH",
      dataIndex: "year_month",
      key: "year_month",
      render: (_, { year_month }) => dayjs(year_month).format("YYYY-MM"),
    },
    {
      title: "STATUS",
      dataIndex: "status",
      key: "status",
      render: (_, { status }) => {
        const findStatus = PUBLICATION_STATUS_OPTIONS.find(
          (s) => s?.value === status
        );
        return (
          <Tag color={findStatus?.color}>
            {findStatus?.label || "Not yet started"}
          </Tag>
        );
      },
    },
    {
      title: "ACTION",
      dataIndex: "publication_id",
      key: "id",
      render: (_, { pk, publication_id, detail_url, status }) => {
        const routeURL = publication_id
          ? status === PUBLICATION_STATUS.in_validation
            ? `/publications/${publication_id}/validation`
            : `/publications/${publication_id}`
          : `/publications/create?cdi_geonode_id=${pk}`;
        return (
          <Space>
            <Button type="link" href={detail_url} target="_blank">
              Open in Geonode
            </Button>

            <Button
              type="primary"
              onClick={() => {
                router.push(routeURL);
              }}
            >
              {publication_id ? "View" : "Start new Publication"}
            </Button>
          </Space>
        );
      },
    },
  ];

  const onChangeStatus = (value) => {
    setLoading(true);
    fetchData(value);
  };

  const fetchData = useCallback(async (status = null) => {
    try {
      const apiURL = status
        ? `/admin/cdi-geonode?status=${status}`
        : "/admin/cdi-geonode";
      const { data, total } = await api("GET", apiURL);
      if (total) {
        setTotalData(total);
      }
      if (data) {
        const _publications = data.map((d) => ({ key: d?.id, ...d }));
        setPublications(_publications);
      }
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);
  return (
    <div className="w-full h-auto space-y-4 pt-6">
      <Flex align="center" justify="space-between">
        <div className="w-2/3">
          <Title level={2}>CDI Publication</Title>
        </div>
        <div className="w-1/3 flex justify-end">
          <Select
            onChange={onChangeStatus}
            options={PUBLICATION_STATUS_OPTIONS}
            className="w-full max-w-48"
            placeholder="Filter by Status"
            allowClear
          />
        </div>
      </Flex>
      <Can I="read" a="Publication">
        <Table
          columns={columns}
          dataSource={publications}
          loading={loading}
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
          rowKey="pk"
        />
      </Can>
      <Modal
        title={preview?.title}
        open={preview?.pk}
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
        {preview?.embed_url && (
          <iframe
            width={"100%"}
            height={600}
            src={preview.embed_url}
            className="min-w-[640px]"
          />
        )}
      </Modal>
    </div>
  );
};

export default PublicationsPage;
