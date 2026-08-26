"use client";

import { useCallback, useEffect, useState } from "react";
import { PageHeader, SubmitButton } from "@/components";
import {
  Alert,
  Button,
  Form,
  Input,
  message,
  Modal,
  Select,
  Skeleton,
  Typography,
} from "antd";
import { useUserContext, useUserDispatch } from "@/context/UserContextProvider";
import { api, storage } from "@/lib";
import dayjs from "dayjs";
import { TWG_OPTIONS, USER_ROLES } from "@/static/config";

const { useForm } = Form;
const { Text } = Typography;

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
  const [preload, setPreload] = useState(true);

  const [form] = useForm();
  const userContext = useUserContext();
  const userDispatch = useUserDispatch();

  const fetchProfile = useCallback(async () => {
    try {
      if (preload) {
        setPreload(false);
        const payload = await api("GET", "/users/me");
        if (payload?.id) {
          userDispatch({
            type: "UPDATE",
            payload,
          });
        }
      }
    } catch (err) {
      setPreload(false);
      console.error(err);
    }
  }, [userDispatch, preload]);

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
    <div className="w-full h-auto">
      <PageHeader
        title="Your profile"
        description="Manage your account details and preferences."
      />

      <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <div className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px]">
          {userContext?.id && !userContext?.email_verified && (
            <div className="mb-4">
              <UnverifiedAlert email={userContext?.email} />
            </div>
          )}
          <section className="border border-cardBorder bg-white max-w-[640px]">
            <div className="border-b border-cardBorder px-4 py-4 sm:px-6">
              <h2 className="text-xl font-semibold leading-7 text-[#333333]">
                Account details
              </h2>
            </div>
            <div className="p-4 sm:p-6">
              <Skeleton loading={!userContext?.id} title paragraph>
                <Form
                  layout="vertical"
                  initialValues={userContext}
                  form={form}
                  onFinish={onFinish}
                >
                  <Form.Item
                    label="Email"
                    name="email"
                    rules={[{ required: true, type: "email" }]}
                  >
                    <Input
                      type="email"
                      placeholder="Your Email"
                      addonAfter={
                        <>
                          {userContext?.email_verified
                            ? "Verified"
                            : "Unverified"}
                        </>
                      }
                    />
                  </Form.Item>
                  <Form.Item
                    label="Full Name"
                    name="name"
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="Your name" />
                  </Form.Item>
                  {userContext?.role === USER_ROLES.reviewer && (
                    <Form.Item
                      name="technical_working_group"
                      label="Technical Working Group"
                      rules={[
                        {
                          required: true,
                          message: "Technical Working Group is required",
                        },
                      ]}
                    >
                      <Select options={TWG_OPTIONS} />
                    </Form.Item>
                  )}
                  <SubmitButton form={form} loading={loading}>
                    Save
                  </SubmitButton>
                </Form>
              </Skeleton>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
