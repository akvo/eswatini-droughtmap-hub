"use client";

import { useState } from "react";
import { Alert, Checkbox, Form, Input } from "antd";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { auth } from "@/lib";
import { PasswordInput, SubmitButton } from "@/components";
import { HOME_PAGE } from "@/static/config";

const { useForm } = Form;

const LoginPage = () => {
  const [submitting, setSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(false);
  const [remember, setRemember] = useState(false);
  const router = useRouter();
  const [form] = useForm();

  const onFinish = async ({ email, password }) => {
    setSubmitting(true);
    try {
      const { status, role } = await auth.signIn({ email, password });
      if (status === 200) {
        router.push(HOME_PAGE?.[role] || "/");
      } else {
        setSubmitting(false);
        setInvalid(true);
      }
    } catch (error) {
      const errorKey = error.message.replace(/^Error:\s*/, "");
      console.error("error", errorKey);
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full flex-1 flex flex-row items-center justify-center py-16">
      <div className="w-[360px] max-w-full mx-auto flex flex-col gap-8">
        <div className="flex flex-col gap-3 text-center">
          <h1 className="text-[28px] leading-[42px] font-bold text-[#333333]">
            Log in to your account
          </h1>
          <p className="text-sm text-[#606060]">Please enter your details.</p>
        </div>

        {invalid && (
          <Alert message="Invalid email or password" type="error" showIcon />
        )}

        <Form layout="vertical" name="login" form={form} onFinish={onFinish}>
          <Form.Item
            label="Email"
            name="email"
            rules={[{ required: true, type: "email" }]}
          >
            <Input type="email" placeholder="Your email" />
          </Form.Item>
          <PasswordInput
            label="Password"
            name="password"
            placeholder="Your password"
            rules={[{ required: true }]}
          />
          <div className="flex items-center justify-between mb-6">
            {/* ponytail: presentational — no "remember" support in auth.signIn */}
            <Checkbox
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
            >
              Remember for 30 days
            </Checkbox>
            <Link href="/forgot-password" className="text-sm text-brandMuted">
              Forgot password
            </Link>
          </div>
          <SubmitButton form={form} loading={submitting} block>
            Sign in
          </SubmitButton>
        </Form>
      </div>
    </div>
  );
};

export default LoginPage;
