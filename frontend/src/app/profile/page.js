"use client";

import { useCallback, useEffect, useState } from "react";
import { SubmitButton } from "@/components";
import { Alert, Form, Input, Typography } from "antd";
import { useUserContext, useUserDispatch } from "@/context/UserContextProvider";
import { api } from "@/lib";

const { useForm } = Form;
const { Title } = Typography;

const ProfilePage = () => {
  const [loading, setLoading] = useState(false);
  const [form] = useForm();
  const userContext = useUserContext();
  const userDispatch = useUserDispatch();

  const fetchProfile = useCallback(async () => {
    if (!userContext?.id) {
      const payload = await api("GET", "/users/me");
      form.setFieldValue("name", payload?.name);
      form.setFieldValue("email", payload?.email);
      userDispatch({
        type: "UPDATE",
        payload,
      });
    }
  }, [userContext]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const payload = await api("PUT", "/users/me", values);
      userDispatch({
        type: "UPDATE",
        payload,
      });
      setLoading(false);
    } catch (error) {
      setLoading(false);
      console.error(error);
    }
  };

  return (
    <div className="w-full md:w-1/2 h-full">
      <Title level={2}>Your profile</Title>
      {userContext?.id && !userContext?.email_verified && (
        <Alert
          message="Warning"
          description="Please verify your email address to activate your account"
          type="warning"
          showIcon
        />
      )}
      <Form layout="vertical" form={form} onFinish={onFinish}>
        <Form.Item
          label="Email"
          name="email"
          rules={[
            {
              required: true,
              type: "email",
            },
          ]}
        >
          <Input
            type="email"
            placeholder="Your Email"
            addonAfter={
              <>{userContext?.email_verified ? "Verified" : "Unverified"}</>
            }
          />
        </Form.Item>
        <Form.Item
          label="Full Name"
          name="name"
          rules={[
            {
              required: true,
            },
          ]}
        >
          <Input placeholder="Your name" />
        </Form.Item>
        <SubmitButton form={form} loading={loading}>
          Save
        </SubmitButton>
      </Form>
    </div>
  );
};

export default ProfilePage;
