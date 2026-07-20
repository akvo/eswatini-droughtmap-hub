"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, Flex, Spin, Tag, Typography } from "antd";
import dayjs from "dayjs";
import { api } from "@/lib";

const { Text } = Typography;

/**
 * Which component rasters (ESI/EVI2/SM/SPI) GeoNode holds for a month.
 *
 * Advisory only: the rasters are attached by a background job after the
 * publication is created, and that job re-reads the catalogue at the time it
 * runs. A missing component here is normally just a timing gap — the CDI
 * pipeline has not published that month yet — so it never blocks the form.
 */
const ComponentRasterPreview = ({ yearMonth }) => {
  const [components, setComponents] = useState(null);
  const [loading, setLoading] = useState(false);

  const onLoad = useCallback(async (value) => {
    if (!value) {
      return;
    }
    setLoading(true);
    try {
      const { data } = await api(
        "GET",
        `/admin/component-rasters?year_month=${dayjs(value).format("YYYY-MM")}`,
      );
      setComponents(data);
    } catch (err) {
      console.error(err);
      // A failed lookup must not block publication creation.
      setComponents(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    onLoad(yearMonth);
  }, [yearMonth, onLoad]);

  return (
    <div className="mb-6 space-y-2">
      <Text type="secondary">Component rasters for this month</Text>
      {loading ? (
        <div className="pt-2">
          <Spin size="small" />
        </div>
      ) : (
        <Flex gap={8} wrap className="pt-2">
          {components?.length ? (
            components.map((c) => (
              <Tag key={c.key} color={c.available ? "green" : "default"}>
                {c.label}
                {c.available ? "" : " — not available"}
              </Tag>
            ))
          ) : (
            <Text type="secondary">No data</Text>
          )}
        </Flex>
      )}

      {components?.some((c) => !c.available) && (
        <Alert
          className="mt-2"
          type="info"
          showIcon
          message={
            "Missing components are attached automatically once the CDI " +
            "pipeline publishes them. You can still create this publication."
          }
        />
      )}
    </div>
  );
};

export default ComponentRasterPreview;
