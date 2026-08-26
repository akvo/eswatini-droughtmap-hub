"use client";

import { Button, Form, Input, message, Result } from "antd";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { SubmitButton } from "@/components";
import { api } from "@/lib";

const { useForm } = Form;

const FeedbackPage = () => {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const router = useRouter();
  const [form] = useForm();

  const handleOnFinish = async (values) => {
    setLoading(true);
    try {
      const { message: apiMessage } = await api("POST", "/feedback", values);
      message.info(apiMessage);
      setSuccess(true);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-[480px] mx-auto px-6 py-16">
      {success ? (
        <Result
          status="success"
          title="Thank you for your feedback!"
          subTitle="Your feedback has been successfully submitted. We appreciate your input and will use it to improve our services."
          extra={
            <Button
              type="primary"
              key="console"
              onClick={() => router.push("/")}
            >
              Go back to home
            </Button>
          }
        />
      ) : (
        <>
          <div className="w-full text-center space-y-3 mb-8">
            <p className="text-base text-primary font-normal">Contact us</p>
            <h1 className="text-3xl xl:text-[40px] xl:leading-[1.4] font-bold text-gray-800">
              Get in touch
            </h1>
            <p className="text-lg xl:text-xl text-gray-600">
              We&apos;d love to hear from you. Please fill out this form.
            </p>
          </div>
          <Form form={form} onFinish={handleOnFinish} layout="vertical">
            <Form.Item
              name="email"
              label="Email"
              rules={[
                {
                  required: true,
                  type: "email",
                },
              ]}
            >
              <Input type="email" placeholder="your@mail.com" />
            </Form.Item>
            <Form.Item
              name="feedback"
              label="Message"
              rules={[
                {
                  required: true,
                },
              ]}
            >
              <Input.TextArea
                rows={5}
                placeholder="Share your thoughts with us..."
              />
            </Form.Item>
            <SubmitButton
              type="primary"
              size="large"
              form={form}
              loading={loading}
              block
            >
              Send a message
            </SubmitButton>
          </Form>
        </>
      )}
    </div>
  );
};

export default FeedbackPage;
