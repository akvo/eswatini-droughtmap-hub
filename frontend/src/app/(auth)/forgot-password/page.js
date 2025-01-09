"use client";

import { Button, Card, Form, Input, Typography } from "antd";
import { useRouter } from "next/navigation";
const { Title, Text } = Typography;

const ForgotPasswordPage = () => {
  const router = useRouter();
  return (
    <Card
      style={{ width: 400 }}
      classNames={{
        header: "text-center",
      }}
      title={<Title level={3}>Forgot Your Password?</Title>}
    >
      <Text className="w-72">
        Enter your email address below and we'll send you a link to reset your
        password.
      </Text>
      <Form layout="vertical">
        <Form.Item label="Email" name="email">
          <Input type="email" placeholder="Your Email" />
        </Form.Item>
        <Button htmlType="submit" type="primary" block>
          Send reset link
        </Button>
        <Button
          htmlType="button"
          type="link"
          onClick={() => router.push("/login")}
          ghost
          block
        >
          Back to Login
        </Button>
      </Form>
    </Card>
  );
};

export default ForgotPasswordPage;
