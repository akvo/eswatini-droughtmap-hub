"use client";

import { ValidationModal, ValidationTable } from "@/components";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import { api, transformReviews } from "@/lib";
import { DROUGHT_CATEGORY_LABEL } from "@/static/config";
import { Button, Skeleton, Tabs, Typography } from "antd";
import dayjs from "dayjs";
import dynamic from "next/dynamic";
import { redirect } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

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

  const { administrations, refreshMap } = useAppContext();
  const appDispatch = useAppDispatch();

  const yearMonth = publication?.year_month
    ? dayjs(publication?.year_month, "YYYY-MM").format("MMMM YYYY")
    : "...";

  const totalValidated = useMemo(() => {
    return publication?.validated_values?.filter(
      (v) => v?.category || v?.category === 0
    )?.length;
  }, [publication?.validated_values]);

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

  const onRefreshMap = useCallback(() => {
    appDispatch({
      type: "REFRESH_MAP_TRUE",
    });
    setTimeout(() => {
      appDispatch({
        type: "REFRESH_MAP_FALSE",
      });
    }, 500);
  }, [appDispatch]);

  const onSelectValue = useCallback(
    async (val, admID) => {
      try {
        const currentValues =
          publication?.validated_values?.length === administrations?.length
            ? publication.validated_values
            : dataSource;
        const payload = {
          validated_values: administrations?.map(({ administration_id }) => {
            const fd = currentValues?.find(
              (v) => v?.administration_id === administration_id
            );
            const category =
              administration_id === admID
                ? val
                : fd?.category === undefined
                ? null
                : fd?.category;
            return {
              category,
              administration_id,
            };
          }),
        };
        const { validated_values } = await api(
          "PUT",
          `/admin/publication/${params?.id}`,
          payload
        );
        if (activeTab === "map") {
          onRefreshMap();
        }

        if (validated_values) {
          setPublication({
            ...publication,
            validated_values,
          });
          const ds = dataSource?.map((d) => {
            const fd = validated_values?.find(
              (v) => v?.administration_id === d?.administration_id
            );
            const category =
              d?.administration_id === admID
                ? val
                : fd?.category === undefined
                ? d?.category
                : fd?.category;
            return {
              ...d,
              category,
            };
          });
          setDataSource(ds);
        }
      } catch (err) {
        console.error(err);
      }
    },
    [
      dataSource,
      administrations,
      activeTab,
      publication,
      onRefreshMap,
      params?.id,
    ]
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

  const onBulkValidation = async (ids = []) => {
    try {
      const payload = {
        validated_values: administrations?.map(({ administration_id }) => {
          const findData = dataSource?.find(
            (d) => d?.administration_id === administration_id
          );
          const category =
            findData?.category === undefined ? null : findData?.category;
          const data = {
            category,
            administration_id,
          };
          if (ids?.includes(administration_id)) {
            return {
              ...data,
              category: findData?.[extraColumns?.[0]?.dataIndex],
            };
          }
          return data;
        }),
      };

      const { validated_values } = await api(
        "PUT",
        `/admin/publication/${params?.id}`,
        payload
      );
      if (validated_values) {
        setPublication({
          ...publication,
          validated_values,
        });
        const ds = dataSource?.map((d) => {
          const fd = validated_values.find(
            (v) => v?.administration_id === d?.administration_id
          );
          const category =
            fd?.category === undefined ? d?.category : fd?.category;
          return {
            ...d,
            category,
          };
        });

        setDataSource(ds);
      }
    } catch (err) {
      console.error(err);
    }
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
          {administrations?.length &&
          administrations.length === totalValidated ? (
            <Button type="primary" size="large">
              Ready to Publish
            </Button>
          ) : (
            <div className="leading-2 text-center">
              <strong>REMAINING Tinkhundla</strong>
              <h2 className="text-2xl">
                {administrations.length && !isNaN(totalValidated)
                  ? administrations.length - totalValidated
                  : "..."}
              </h2>
            </div>
          )}
        </div>
      </div>
      <Tabs
        activeKey={activeTab}
        onChange={(key) => {
          if (key === "map") {
            onRefreshMap();
          }
          setActiveTab(key);
        }}
        items={[
          {
            key: "table",
            label: "Table View",
            children: (
              <Skeleton loading={loading} title paragraph>
                <ValidationTable
                  data={dataSource}
                  {...{
                    extraColumns,
                    onDetails,
                    onSelectValue,
                    onNonDisputed,
                    onNonValidated,
                    onBulkValidation,
                  }}
                />
              </Skeleton>
            ),
          },
          {
            key: "map",
            label: "Map View",
            children: (
              <ValidationMap {...{ refreshMap, dataSource, onDetails }} />
            ),
          },
        ]}
      />
      <ValidationModal
        data={activeModal}
        isOpen={activeModal?.administration_id}
        onClose={() => setActiveModal(null)}
        onSelectValue={onSelectValue}
      />
    </div>
  );
};

export default ValidationPage;
