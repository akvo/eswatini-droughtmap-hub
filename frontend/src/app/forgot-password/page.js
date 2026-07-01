"use client";

import { SubmitButton } from "@/components";
import { api } from "@/lib";
import { Form, Input, message } from "antd";
import Link from "next/link";
import { useState } from "react";

const { useForm } = Form;

const ForgotPasswordPage = () => {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form] = useForm();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const { message: res } = await api(
        "POST",
        "/auth/forgot-password",
        values,
      );
      if (res === "OK") {
        setSuccess(true);
        setLoading(false);
      } else {
        message.error(res);
        setLoading(false);
      }
    } catch (error) {
      setLoading(false);
      console.error(error);
    }
  };

  return (
    <div className="w-full flex-1 flex flex-row items-center justify-center py-16">
      <div className="w-[360px] max-w-full mx-auto flex flex-col gap-8">
        {success ? (
          <div className="flex flex-col gap-3 text-center">
            <h1 className="text-[28px] leading-[42px] font-bold text-[#333333]">
              Email sent successfully
            </h1>
            <p className="text-sm text-[#606060]">
              Please check your email to reset your password.
            </p>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-3 text-center">
              <h1 className="text-[28px] leading-[42px] font-bold text-[#333333]">
                Forgot your password?
              </h1>
              <p className="text-sm text-[#606060]">
                Enter your email address below and we&apos;ll send you a link to
                reset your password.
              </p>
            </div>
            <Form layout="vertical" form={form} onFinish={onFinish}>
              <Form.Item
                label="Email"
                name="email"
                rules={[{ required: true, type: "email" }]}
              >
                <Input type="email" placeholder="Your email" />
              </Form.Item>
              <SubmitButton form={form} loading={loading} block>
                Send reset link
              </SubmitButton>
            </Form>
          </>
        )}
        <Link href="/login" className="text-center text-sm text-brandMuted">
          Back to Login
        </Link>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
