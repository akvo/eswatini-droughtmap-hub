"use client";

import { Button, Form, Input, message, Result } from "antd";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogoSection, Navbar, SubmitButton } from "@/components";
import { api, auth } from "@/lib";

const { useForm } = Form;

const FeedbackPage = () => {
  const [currentUser, setCurrentUser] = useState(null);
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
    console.log(values);
  };

  const loadCurrentUser = useCallback(async () => {
    const session = await auth.getSession();
    setCurrentUser(session);
  }, []);

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  return (
    <div className="w-full min-h-screen">
      <Navbar session={currentUser} />
      <div className="container w-full h-full relative space-y-4 xl:space-y-8 pt-3 pb-9">
        <div className="w-full space-y-2">
          <div className="w-full border-b border-b-neutral-200 pb-4">
            <h1 className="text-2xl xl:text-3xl font-bold text-gray-800">
              Feedback
            </h1>
          </div>
        </div>
        <div className="w-full flex">
          <div className="w-3/5 pr-4">
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
              <Form form={form} onFinish={handleOnFinish} layout="vertical">
                <Form.Item
                  name="email"
                  label="Your E-mail"
                  placeholder="Your E-mail"
                  rules={[
                    {
                      required: true,
                      type: "email",
                    },
                  ]}
                >
                  <Input type="email" />
                </Form.Item>
                <Form.Item
                  name="feedback"
                  label="Your feedback"
                  placeholder="Your feedback"
                  rules={[
                    {
                      required: true,
                    },
                  ]}
                >
                  <Input.TextArea />
                </Form.Item>
                <div>
                  <SubmitButton
                    htmlType="sbmit"
                    type="primary"
                    size="large"
                    form={form}
                    loading={loading}
                  >
                    Send Feedback
                  </SubmitButton>
                </div>
              </Form>
            )}
          </div>
          <div className="w-2/5 pl-4">
            <div className="bg-gray-100 p-4 rounded-lg">
              <h2 className="text-xl font-semibold mb-4">
                How to Send Feedback
              </h2>
              <p className="mb-2 text-sm">
                To ensure your feedback is helpful and constructive, please
                consider the following guidelines:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm ml-4">
                <li>Be clear and concise in your message.</li>
                <li>
                  Provide specific examples or details to support your feedback.
                </li>
                <li>Be respectful and courteous in your language.</li>
                <li>Focus on the issue, not the person.</li>
                <li>Suggest possible solutions or improvements.</li>
              </ul>
              <p className="mt-4 text-sm">
                Your feedback will be sent to all Eswatini Drought Monitor
                admins. Thank you for helping us improve!
              </p>
            </div>
          </div>
        </div>
      </div>
      <LogoSection />
    </div>
  );
};

export default FeedbackPage;
