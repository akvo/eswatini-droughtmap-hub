"use client";

import dynamic from "next/dynamic";
import { SubmitButton } from "@/components";
import { Checkbox, Form, Input, message, Modal, Space, Typography } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import CDIMap from "@/components/Map/CDIMap";
import dayjs from "dayjs";
import { api } from "@/lib";
import { useRouter } from "next/navigation";
import { PUBLICATION_STATUS } from "@/static/config";
import classNames from "classnames";

const TinyEditor = dynamic(() => import("@/components/TinyEditor"), {
  ssr: false,
});

const { useForm } = Form;
const { Title } = Typography;

const PublishPage = ({ params }) => {
  const [loading, setLoading] = useState(false);
  const [narrative, setNarrative] = useState("");
  const [publication, setPublication] = useState(null);
  const [settings, setSettings] = useState({
    map: true,
    editor: true,
  });

  const [form] = useForm();
  const router = useRouter();

  const yearMonth = useMemo(() => {
    if (publication?.year_month) {
      return dayjs(publication?.year_month, "YYYY-MM").format("MMMM YYYY");
    }
    return "...";
  }, [publication]);

  const onFinish = async (payload) => {
    setLoading(true);
    try {
      const apiData = await api("PUT", `/admin/publication/${params.id}`, {
        bulletin_url: payload?.bulletin_url,
        narrative: payload?.narrative,
        status: PUBLICATION_STATUS.published,
      });
      if (apiData?.status === PUBLICATION_STATUS.published) {
        router.push(`/publications/${params.id}`);
      } else {
        message.error(
          "[ADM-P-3] Please report this issue along with the code."
        );
      }
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const onConfirm = (payload) => {
    Modal.confirm({
      title: `Publish SPI Map for: ${yearMonth}`,
      content: "Are you sure?",
      onOk: () => onFinish(payload),
    });
  };

  const fetchData = useCallback(async () => {
    try {
      const apiData = await api("GET", `/admin/publication/${params?.id}`);
      if (!apiData?.id) {
        redirect("/publications");
      }
      form.setFieldValue("year_month", apiData.year_month);
      form.setFieldValue("bulletin_url", apiData.bulletin_url);
      setPublication(apiData);
    } catch (err) {
      console.error(err);
    }
  }, [params?.id, form]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="w-full pt-3">
      <div className="w-full flex flex-row align-center justify-between">
        <div>
          <Title
            level={2}
          >{`Inkundla SPI Publication for: ${yearMonth}`}</Title>
        </div>
        <div className="w-fit">
          <Space>
            <Checkbox
              onClick={() => {
                setSettings({
                  ...settings,
                  map: !settings.map,
                });
              }}
              checked={settings.map}
            >
              Show Map
            </Checkbox>
            <Checkbox
              onClick={() => {
                setSettings({
                  ...settings,
                  editor: !settings.editor,
                });
              }}
              checked={settings.editor}
            >
              Show Editor
            </Checkbox>
          </Space>
        </div>
      </div>
      <div className="w-full flex flex-col lg:flex-row align-center justify-start">
        <div
          className={classNames({
            "lg:w-1/2": settings.editor && settings.map,
            hidden: !settings.map,
            "w-full": !settings.editor && settings.map,
          })}
        >
          {settings.map && (
            <CDIMap>
              <div
                className={classNames(
                  "absolute top-0 right-0 z-10 p-2 space-y-4",
                  {
                    "w-1/3": !settings.editor && settings.map,
                    "w-1/2": settings.editor && settings.map,
                  }
                )}
              >
                <CDIMap.Legend />
              </div>
            </CDIMap>
          )}
        </div>
        <div
          className={classNames({
            "lg:w-1/2 border-l border-1-neutral-200 pl-12":
              settings.editor && settings.map,
            hidden: !settings.editor,
            "w-10/12": settings.editor && !settings.map,
          })}
        >
          <Title level={3}>Publication Form</Title>
          <Form
            form={form}
            onFinish={(payload) => onConfirm(payload)}
            layout="vertical"
            className="w-full"
          >
            <Form.Item name="year_month" label="Year Month">
              <Input placeholder="YYYY-MM" readOnly />
            </Form.Item>
            <Form.Item name="bulletin_url" label="Bulletin URL">
              <Input placeholder="http://..." />
            </Form.Item>
            <Form.Item
              name="narrative"
              label="Narrative"
              rules={[
                {
                  required: true,
                },
              ]}
            >
              <TinyEditor
                value={narrative}
                setValue={(value) => {
                  form.setFieldValue("narrative", value);
                  setNarrative(value);
                }}
                height={350}
              />
            </Form.Item>
            <div className="py-4 float-right">
              <SubmitButton form={form} loading={loading} size="large">
                Publish
              </SubmitButton>
            </div>
          </Form>
        </div>
      </div>
    </div>
  );
};

export default PublishPage;
