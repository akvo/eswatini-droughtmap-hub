"use client";

import {
  DROUGHT_CATEGORY,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";
import { Badge, Divider, Form, List, Modal, Select } from "antd";
import { useMemo, useState } from "react";

const ValidationModal = ({
  isOpen = false,
  data = {},
  onClose,
  onSelectValue,
}) => {
  const [loading, setLoading] = useState(false);
  const [value, setValue] = useState(data?.category);

  const onSave = async () => {
    setLoading(true);
    await onSelectValue(value, data?.administration_id);
    setValue(null);
    setLoading(false);
    onClose();
  };

  const activeComments = useMemo(() => {
    if (data?.administration_id) {
      return Object.keys(data)
        .filter((k) => k.includes("_comment"))
        .map((k) => data[k]);
    }
    return [];
  }, [data]);

  return (
    <Modal
      title={<span className="text-2xl">{data?.name}</span>}
      open={isOpen}
      onCancel={onClose}
      onOk={onSave}
      maskClosable={false}
      width={768}
      okText="Save"
      okButtonProps={{
        loading,
      }}
      cancelText="Close"
      destroyOnClose
      closable
    >
      <Divider orientation="center">
        <strong>All Comments</strong>
      </Divider>
      <List
        dataSource={activeComments}
        renderItem={(item) => (
          <Badge.Ribbon
            text={DROUGHT_CATEGORY_LABEL?.[item?.category]}
            color={DROUGHT_CATEGORY_COLOR?.[item?.category]}
            style={{
              color: item?.category < 4 ? "#212121" : "#ffffff",
            }}
          >
            <List.Item>
              <List.Item.Meta
                title={
                  <div className="flex flex-col">
                    <strong>{item?.twg}</strong>
                    <small>{item?.user}</small>
                  </div>
                }
                description={item?.comment || "No comment"}
              />
            </List.Item>
          </Badge.Ribbon>
        )}
      />
      <Divider orientation="center">
        <strong>Validation Form</strong>
      </Divider>
      <Form>
        <Form.Item label="Computed Value">
          <Select
            options={DROUGHT_CATEGORY}
            placeholder="Computed Value"
            className="w-full"
            defaultValue={data?.initial_category}
            allowClear
            disabled
          />
        </Form.Item>
        <Form.Item label="Validated SPI Value">
          <Select
            options={DROUGHT_CATEGORY.slice(0, DROUGHT_CATEGORY.length - 1)}
            placeholder="Select Drought category"
            className="w-full"
            defaultValue={data?.category}
            onChange={setValue}
            allowClear
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ValidationModal;
