"use client";

import { SubmitButton } from "@/components";
import { MinusCircleIcon, PlusCircleIcon } from "@/components/Icons";
import { api } from "@/lib";
import { Button, Divider, Flex, Form, Input, Space, Typography } from "antd";
import { useCallback, useEffect, useState } from "react";

const { Title, Text } = Typography;
const { useForm } = Form;

const EmailListForm = ({ label, name }) => (
  <Form.List
    name={name}
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
      <div className="w-full">
        <Flex align="center" justify="space-between">
          <div>
            <Text strong>{label}</Text>
          </div>
          <div>
            <Button
              type="dashed"
              onClick={() => add()}
              icon={<PlusCircleIcon />}
            >
              Add new
            </Button>
          </div>
        </Flex>
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
                className="w-full"
              >
                <Input placeholder="Email" type="email" className="w-full" />
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
          <Form.ErrorList errors={errors} />
        </Form.Item>
      </div>
    )}
  </Form.List>
);

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    on_success_emails: [null],
    on_failure_emails: [null],
    on_exceeded_emails: [null],
  });
  const [loading, setLoading] = useState(false);
  const [form] = useForm();

  const onFinish = async (payload) => {
    setLoading(true);
    try {
      console.log("payload", payload);
      // const apiData = await api("PUT", "/settings", payload);
      // setSettings(apiData);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  // const fetchData = useCallback(async () => {
  //   try {
  //     const apiData = await api("GET", "/settings");

  //     setSettings(apiData);
  //     if (apiData?.on_failure_emails) {
  //       form.setFieldValue("on_failure_emails", apiData.on_failure_emails);
  //     }
  //   } catch (err) {
  //     console.error(err);
  //   }
  // }, [form]);

  // useEffect(() => {
  //   fetchData();
  // }, [fetchData]);

  return (
    <div className="w-full h-auto space-y-4 pt-6">
      <Title level={2}>Settings</Title>
      <div className="w-full h-auto flex flex-col lg:flex-row align-start justify-between gap-6">
        <div className="w-full lg:w-4/12 space-y-2">
          <Title level={3}>Email Notifications</Title>
          <Form form={form} initialValues={settings} onFinish={onFinish}>
            <EmailListForm
              label="On Success (DH Admins)"
              name="on_success_emails"
            />
            <EmailListForm
              label="On Failure (Technical Support)"
              name="on_failure_emails"
            />
            <EmailListForm label="On Job Exceeded" name="on_exceeded_emails" />

            <div className="w-full text-right">
              <SubmitButton size="large" form={form} loading={loading}>
                Save
              </SubmitButton>
            </div>
          </Form>
        </div>
        <div className="w-full lg:w-8/12 border-l border-l-grey-100 px-6">
          <Title level={3}>CDI Automation Jobs</Title>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
