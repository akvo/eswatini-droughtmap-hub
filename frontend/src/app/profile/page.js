"use client";

import { useCallback, useEffect, useState } from "react";
import { SubmitButton } from "@/components";
import { Alert, Button, Form, Input, message, Modal, Typography } from "antd";
import { useUserContext, useUserDispatch } from "@/context/UserContextProvider";
import { api, storage } from "@/lib";
import dayjs from "dayjs";

const { useForm } = Form;
const { Title, Text } = Typography;

const UnverifiedAlert = ({ email }) => {
  const [isSent, setIsSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const resendVerify = storage.get("RESEND_VERIFY");

  const handleOnClick = async () => {
    setLoading(true);
    try {
      await api("POST", "/email/resend-verify", {
        email,
      });
      message.success("Verification email resent successfully.");
      storage.set("RESEND_VERIFY", dayjs().add(1, "hour").toISOString());

      setIsSent(true);
      setLoading(false);
    } catch (error) {
      setLoading(false);
      console.error(error);
      message.error("Failed to resend verification email.");
    }
  };
  return (
    <Alert
      message="Warning"
      description={
        <>
          {isSent || (resendVerify && dayjs().isBefore(dayjs(resendVerify))) ? (
            <>
              Verification email sent. Please wait until 1 hour before
              requesting again.
            </>
          ) : (
            <>
              {`Please verify your email address to activate your account. Didn\'t receive the email?`}
              <Button type="link" onClick={handleOnClick} loading={loading}>
                Resend Verification Email
              </Button>
            </>
          )}
        </>
      }
      type="warning"
      showIcon
    />
  );
};

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
  }, [userContext, userDispatch, form]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const payload = await api("PUT", "/users/me", values);

      if (values?.email !== userContext?.email) {
        Modal.success({
          content: (
            <>
              <Text>
                Verification email has been sent to your new email address.
              </Text>
              <Text>Please verify to activate your account.</Text>
            </>
          ),
        });
      } else {
        message.success("Profile updated successfully.");
      }
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
    <div className="w-full md:w-1/2 h-full space-y-4">
      <Title level={2}>Your profile</Title>
      {userContext?.id && !userContext?.email_verified && (
        <UnverifiedAlert email={userContext?.email} />
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
