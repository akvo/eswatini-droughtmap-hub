"use client";

import { DROUGHT_CATEGORY_COLOR } from "@/static/config";
import { api } from "@/lib";
import { Skeleton } from "antd";
import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import FeatureInfoCard from "@/components/Map/FeatureInfoCard";

const CDIMap = dynamic(() => import("@/components/Map/CDIMap"), { ssr: false });

const IframeMapPage = ({ searchParams }) => {
  const { id } = searchParams;
  const [preload, setPreload] = useState(true);
  const [currentID, setCurrentID] = useState(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [selectedFeature, setSelectedFeature] = useState(null);

  const checkCurrentID = useCallback(() => {
    if (currentID && id && currentID !== id && !preload) {
      setCurrentID(id);
      setPreload(true);
      setSelectedFeature(null);
    }
  }, [currentID, id, preload]);

  const fetchData = useCallback(async () => {
    try {
      if (preload) {
        setPreload(false);
        if (!isNaN(id)) {
          setLoading(true);
          const { validated_values } = await api("GET", `/map/${id}`);
          if (validated_values) {
            setData(validated_values);
          }
          setLoading(false);
        }
      }
    } catch (err) {
      console.error(err);
      setPreload(false);
    }
  }, [id, preload]);

  const findAdm = (feature) =>
    data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id,
    );

  const onFeature = (feature) => ({
    fillColor: DROUGHT_CATEGORY_COLOR?.[findAdm(feature)?.category] || "white",
  });

  const onClick = (feature) => {
    setSelectedFeature({
      name: feature?.properties?.name,
      category: findAdm(feature)?.category,
    });
  };

  useEffect(() => {
    checkCurrentID();
  }, [checkCurrentID]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <Skeleton.Image style={{ width: "100vw", height: "100vh" }} active />
    );
  }

  return (
    <div className="w-full">
      <CDIMap
        layerKey={data.map((d) => d?.category).join("-")}
        onFeature={onFeature}
        onClick={onClick}
        dragging={false}
        isFullHeight
      >
        <FeatureInfoCard
          feature={selectedFeature}
          onClose={() => setSelectedFeature(null)}
        />
      </CDIMap>
    </div>
  );
};

export default IframeMapPage;
