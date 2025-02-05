"use client";

import { ValidationModal, ValidationTable } from "@/components";
import { useAppContext } from "@/context/AppContextProvider";
import { api, transformReviews } from "@/lib";
import { DROUGHT_CATEGORY_LABEL } from "@/static/config";
import { Button, Skeleton, Tabs, Typography } from "antd";
import dayjs from "dayjs";
import dynamic from "next/dynamic";
import { redirect } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const ValidationMap = dynamic(() => import("@/components/Map/ValidationMap"), {
  ssr: false,
});

const { Title } = Typography;

const ValidationPage = ({ params }) => {
  const [activeTab, setActiveTab] = useState("table");
  const [publication, setPublication] = useState(null);
  const [dataSource, setDataSource] = useState([]);
  const [extraColumns, setExtraColumns] = useState([]);
  const [preload, setPreload] = useState(true);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    nonDisputed: false,
    nonValidated: false,
  });
  const [activeModal, setActiveModal] = useState(null);

  const { administrations } = useAppContext();

  const yearMonth = publication?.year_month
    ? dayjs(publication?.year_month, "YYYY-MM").format("MMMM YYYY")
    : "...";

  const onFilter = async (nonDisputed, nonValidated) => {
    try {
      const { validated_values, reviews, users } = await api(
        "GET",
        `/admin/publication-reviews/${params.id}?non_disputed=${nonDisputed}&non_validated=${nonValidated}`
      );
      setDataSource(
        transformReviews(administrations, reviews, users, {
          ...publication,
          validated_values,
        })
      );
    } catch (err) {
      console.error(err);
    }
  };

  const onSelectValue = useCallback(
    async (val, administration_id) => {
      try {
        const payload = {
          validated_values: administrations?.map((a) => {
            const findCategory = dataSource?.find(
              (d) => d?.administration_id === a?.administration_id
            );
            return {
              category:
                a?.administration_id === administration_id
                  ? val
                  : findCategory?.category === undefined
                  ? null
                  : findCategory?.category,
              administration_id: a?.administration_id,
            };
          }),
        };
        const apiData = await api(
          "PUT",
          `/admin/publication/${params?.id}`,
          payload
        );
        if (apiData?.validated_values) {
          const ds = dataSource?.map((d) => {
            return {
              ...d,
              category:
                d?.administration_id === administration_id ? val : d?.category,
            };
          });
          setDataSource(ds);
        }
      } catch (err) {
        console.error(err);
      }
    },
    [dataSource, administrations, params?.id]
  );

  const onNonDisputed = async (isChecked = false) => {
    setFilter({
      ...filter,
      nonDisputed: isChecked,
    });
    await onFilter(isChecked, filter.nonValidated);
  };

  const onNonValidated = async (isChecked = false) => {
    setFilter({
      ...filter,
      nonValidated: isChecked,
    });
    await onFilter(filter.nonDisputed, isChecked);
  };

  const onDetails = (record) => {
    setActiveModal(record);
  };

  const fetchData = useCallback(async () => {
    if (!preload || administrations?.length === 0) {
      return;
    }
    try {
      setPreload(false);
      const apiData = await api("GET", `/admin/publication/${params?.id}`);
      if (!apiData?.id) {
        redirect("/publications");
      }
      setPublication(apiData);
      const { reviews, users } = await api(
        "GET",
        `/admin/publication-reviews/${params.id}`
      );
      setDataSource(transformReviews(administrations, reviews, users, apiData));
      setExtraColumns(
        users.map((r) => ({
          title: r?.technical_working_group,
          dataIndex: r?.id,
          render: (value) => DROUGHT_CATEGORY_LABEL?.[value],
          width: 192,
        }))
      );
      setLoading(false);
    } catch (err) {
      setPreload(false);
      setLoading(false);
      console.error(err);
    }
  }, [params?.id, preload, administrations]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="w-full">
      <div className="w-full py-3 flex flex-row align-center justify-between">
        <div>
          <Title level={2}>{`Inkundla CDI Validation for: ${yearMonth}`}</Title>
        </div>
        <div>
          <Button type="primary" size="large" disabled>
            Ready to Publish
          </Button>
        </div>
      </div>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: "table",
            label: "Table View",
            children: (
              <>
                <Skeleton loading={loading} title paragraph>
                  <ValidationTable
                    data={dataSource}
                    {...{
                      extraColumns,
                      onDetails,
                      onSelectValue,
                      onNonDisputed,
                      onNonValidated,
                    }}
                  />
                </Skeleton>
                <ValidationModal
                  data={activeModal}
                  isOpen={activeModal?.administration_id}
                  onClose={() => setActiveModal(null)}
                  onSelectValue={onSelectValue}
                />
              </>
            ),
          },
          {
            key: "map",
            label: "Map View",
            children: <ValidationMap />,
          },
        ]}
      />
    </div>
  );
};

export default ValidationPage;
