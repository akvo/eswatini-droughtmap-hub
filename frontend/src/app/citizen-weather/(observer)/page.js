"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Alert, Form, Input } from "antd";
import { SubmitButton } from "@/components";
import { auth } from "@/lib";

const { useForm } = Form;

const SignInPage = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [loading, setLoading] = useState(!!token);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);
  const [form] = useForm();

  useEffect(() => {
    if (!token) return;
    auth.signInWithToken(token).then((result) => {
      if (result.status === 200) {
        router.replace("/citizen-weather/observe");
      } else {
        setError("expired");
        setLoading(false);
        router.replace("/citizen-weather", { scroll: false });
      }
    });
  }, [token, router]);

  const onFinish = async ({ email }) => {
    setLoading(true);
    setError(null);
    setSent(false);
    try {
      const res = await fetch(
        `/api/v1/auth/observer/request-link?format=json`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        },
      );
      if (res.status === 429) {
        setError("throttled");
      } else {
        setSent(true);
      }
    } catch {
      setError("network");
    } finally {
      setLoading(false);
    }
  };

  if (token && loading) {
    return (
      <div className="w-full min-h-screen flex items-center justify-center">
        <p className="text-sm text-[#606060]">Signing you in…</p>
      </div>
    );
  }

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

        {error === "expired" && (
          <Alert
            message="Link expired"
            description="That link has expired. Enter your email below for a fresh one."
            type="warning"
            showIcon
          />
        )}

        {error === "throttled" && (
          <Alert
            message="Too many requests"
            description="Please try again later."
            type="error"
            showIcon
          />
        )}

        {error === "network" && (
          <Alert
            message="Network error"
            description="Could not reach the server. Please check your connection."
            type="error"
            showIcon
          />
        )}

        {sent && (
          <Alert
            message="Sign-in link sent"
            description="Check your inbox for the sign-in link. It expires in 7 days."
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
