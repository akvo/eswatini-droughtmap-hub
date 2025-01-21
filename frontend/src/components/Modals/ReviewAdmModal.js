"use client";

import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import {
  Modal,
  Form,
  Flex,
  Input,
  Select,
  Typography,
  Tag,
  message,
  Button,
} from "antd";

import { DROUGHT_CATEGORY } from "@/static/config";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib";

const { TextArea } = Input;
const { useForm } = Form;
const { Title, Text } = Typography;

const ReviewAdmModal = ({ review }) => {
  const [showSuggestion, setShowSuggestion] = useState(false);
  const { activeAdm } = useAppContext();
  const appDispatch = useAppDispatch();
  const [form] = useForm();
  const router = useRouter();
  const findCategory = DROUGHT_CATEGORY.find(
    (c) =>
      (c?.value === activeAdm?.initial_category && !activeAdm?.reviewed) ||
      (c?.value === activeAdm?.category && activeAdm?.reviewed)
  );

  const isModalOpen = useMemo(() => {
    return activeAdm?.administration_id ? true : false;
  }, [activeAdm]);

  const onFinish = async (values) => {
    try {
      const suggestion_values = review?.suggestion_values?.map((s) => {
        if (activeAdm?.administration_id === s?.administration_id) {
          return {
            ...s,
            ...values,
            category:
              !values?.category && values?.category !== 0
                ? activeAdm?.initial_category
                : values?.category,
            reviewed: true,
          };
        }
        return s;
      });
      await api("PUT", `/reviewer/review/${review?.id}`, {
        suggestion_values,
      });
      appDispatch({
        type: "REFRESH_MAP_TRUE",
      });
      onClose();
      setTimeout(() => {
        appDispatch({
          type: "REFRESH_MAP_FALSE",
        });
      }, 500);
      router.refresh(`/reviews/${review?.id}`);
    } catch (err) {
      message.error("An error occurred, please report this issue!");
      console.error(err);
    }
  };

  const onClose = () => {
    setShowSuggestion(false);
    form.resetFields();
    appDispatch({
      type: "REMOVE_ACTIVE_ADM",
    });
  };

  const updateForm = useCallback(() => {
    if (
      activeAdm?.administration_id &&
      activeAdm?.comment !== form.getFieldValue("comment")
    ) {
      form.setFieldValue("comment", activeAdm?.comment);
    }
  }, [activeAdm, form]);

  useEffect(() => {
    updateForm();
  }, [updateForm]);

  return (
    <>
      <Modal
        title={"INKHUNDLA STATUS"}
        open={isModalOpen}
        onCancel={onClose}
        maskClosable={false}
        width={768}
        footer={
          <Flex
            align="center"
            justify={review?.is_completed ? "end" : "space-between"}
          >
            {!review?.is_completed && (
              <Button
                key="close"
                type="primary"
                onClick={() => {
                  if (activeAdm?.reviewed) {
                    setShowSuggestion(true);
                    appDispatch({
                      type: "UPDATE_ACTIVE_ADM",
                      payload: {
                        reviewed: false,
                      },
                    });
                  } else {
                    setShowSuggestion(!showSuggestion);
                  }
                }}
                ghost
              >
                {activeAdm?.reviewed
                  ? "Edit"
                  : showSuggestion
                  ? "Cancel"
                  : "Suggest new value"}
              </Button>
            )}

            <Button
              key="submit"
              type="primary"
              onClick={() => {
                if (!activeAdm?.reviewed) {
                  form.submit();
                } else {
                  onClose();
                }
              }}
            >
              {activeAdm?.reviewed ? "OK" : "Approve"}
            </Button>
          </Flex>
        }
        destroyOnClose
      >
        <div className="w-full space-y-3">
          <Flex align="center" justify="space-between">
            <Title level={4} className="pt-2">
              {activeAdm?.name}
            </Title>

            <Tag color={activeAdm?.reviewed ? "green" : null}>
              {activeAdm?.reviewed ? "Reviewed" : "Not Reviewed"}
            </Tag>
          </Flex>

          <Form initialValues={activeAdm} form={form} onFinish={onFinish}>
            {activeAdm?.reviewed ? (
              <Form.Item label="Current CDI Value" name="category">
                <Text strong>{findCategory?.label}</Text>
              </Form.Item>
            ) : (
              <Flex align="center" justify="space-between">
                <Form.Item label="Initial CDI Value" name="initial_category">
                  <Text strong>{findCategory?.label}</Text>
                </Form.Item>
                {showSuggestion && (
                  <Form.Item label="Suggested CDI Value" name="category">
                    <Select
                      options={DROUGHT_CATEGORY}
                      placeholder="Select Drought category"
                      disabled={activeAdm?.reviewed}
                      allowClear
                    />
                  </Form.Item>
                )}
              </Flex>
            )}
            <Form.Item name="comment">
              <TextArea
                placeholder={activeAdm?.reviewed ? "" : "Add a comment"}
                disabled={review?.is_completed || activeAdm?.reviewed}
              />
            </Form.Item>
          </Form>
        </div>
      </Modal>
    </>
  );
};

export default ReviewAdmModal;
