"use client";

import { useState } from "react";
import { Alert, Form, Input, message } from "antd";
import { SubmitButton } from "@/components";

const { useForm } = Form;

const SignInPage = () => {
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [form] = useForm();

  const onFinish = ({ email }) => {
    setLoading(true);
    setTimeout(() => {
      message.success("Sign-in link sent! Check your email.");
      setLoading(false);
      setSent(true);
    }, 1500);
  };

  return (
    <div className="w-full min-h-screen flex items-center justify-center py-16 relative">
      <div className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none" />
      <div className="w-[360px] max-w-full mx-auto flex flex-col gap-8 relative z-10">
        <div className="flex flex-col gap-3 text-center">
          <h1 className="text-[28px] leading-[42px] font-bold text-[#333333]">
            Citizen Science Weather
          </h1>
          <p className="text-sm text-[#606060]">
            Enter the email address linked to your weather station and
            we&apos;ll send you a fresh sign-in link.{" "}
            <b>No password to remember.</b>
          </p>
        </div>

        {sent && (
          <Alert
            message="Sign-in link sent"
            description="Check your inbox for the sign-in link. It expires in 24 hours."
            type="success"
            showIcon
          />
        )}

        <Form
          layout="vertical"
          name="cw-signin"
          form={form}
          onFinish={onFinish}
        >
          <Form.Item
            label="Email"
            name="email"
            rules={[
              { required: true, message: "Please enter your email address." },
              { type: "email", message: "Please enter a valid email." },
            ]}
          >
            <Input
              type="email"
              placeholder="sipho.dlamini@example.sz"
              size="large"
            />
          </Form.Item>
          <SubmitButton form={form} loading={loading} block>
            Send me a sign-in link
          </SubmitButton>
        </Form>

        <div
          style={{
            padding: "14px 16px",
            background: "var(--cw-cream)",
            borderRadius: 8,
            fontSize: 12,
            color: "var(--cw-text2)",
            lineHeight: 1.55,
          }}
        >
          <b>How this works</b> &middot; Each observer looks after one weather
          station. You receive a monthly reminder email with a one-click link
          &mdash; no password. If you&apos;ve lost that email, request a new
          link here.
        </div>

        <div
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "var(--cw-text3)",
          }}
        >
          If you don&apos;t have an account yet, contact UNESWA or NDRMA.
        </div>
      </div>
    </div>
  );
};

export default SignInPage;
