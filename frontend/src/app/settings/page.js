"use client";

import { SubmitButton } from "@/components";
import { MinusCircleIcon, PlusCircleIcon } from "@/components/Icons";
import { api } from "@/lib";
import { Button, Flex, Form, Input, Space, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";

const { Title, Text } = Typography;
const { useForm } = Form;

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    ts_emails: [null],
  });
  const [loading, setLoading] = useState(false);
  const [form] = useForm();

  const onFinish = async (payload) => {
    setLoading(true);
    try {
      const apiData = await api("PUT", "/settings", payload);
      setSettings(apiData);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const fetchData = useCallback(async () => {
    try {
      const apiData = await api("GET", "/settings");

      setSettings(apiData);
      if (apiData?.ts_emails) {
        form.setFieldValue("ts_emails", apiData.ts_emails);
      }
    } catch (err) {
      console.error(err);
    }
  }, [form]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="w-1/2 h-auto space-y-4 pt-6">
      <Flex align="center" justify="space-between">
        <div className="w-2/3">
          <Title level={2}>Settings</Title>
        </div>
      </Flex>
      <Form form={form} initialValues={settings} onFinish={onFinish}>
        <Flex gap={16}>
          <div>
            <Text strong>Technical Support Contacts:</Text>
          </div>
          <div>
            <Form.List
              name="ts_emails"
              rules={[
                {
                  validator: async (_, names) => {
                    if (!names || names.length < 1) {
                      return Promise.reject(new Error("At least 1 emails"));
                    }
                  },
                },
              ]}
            >
              {(fields, { add, remove }, { errors }) => (
                <>
                  {fields.map(({ key, ...field }) => (
                    <Flex key={key} vertical>
                      <Space className="w-full mb-4">
                        <Form.Item
                          {...field}
                          validateTrigger={["onChange", "onBlur"]}
                          rules={[
                            {
                              required: true,
                              whitespace: true,
                              type: "email",
                              message: "This is not a valid email",
                            },
                          ]}
                        >
                          <Input
                            placeholder="Email"
                            type="email"
                            className="w-full"
                          />
                        </Form.Item>
                        {fields.length > 0 ? (
                          <a
                            role="button"
                            onClick={(e) => {
                              e.preventDefault();
                              remove(field.name);
                            }}
                          >
                            <MinusCircleIcon />
                          </a>
                        ) : null}
                      </Space>
                    </Flex>
                  ))}
                  <Form.Item>
                    <Button
                      type="dashed"
                      onClick={() => add()}
                      icon={<PlusCircleIcon />}
                    >
                      Add new
                    </Button>

                    <Form.ErrorList errors={errors} />
                  </Form.Item>
                </>
              )}
            </Form.List>
          </div>
        </Flex>
        <SubmitButton size="large" form={form} loading={loading}>
          Save
        </SubmitButton>
      </Form>
    </div>
  );
};

export default SettingsPage;
