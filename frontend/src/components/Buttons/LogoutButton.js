"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "antd";
import { auth } from "@/lib";

const LogoutButton = () => {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const onLogout = async () => {
    setLoading(true);
    await auth.signOut();
    router.push("/");
  };
  return (
    <Button htmlType="button" onClick={onLogout} loading={loading} ghost>
      Logout
    </Button>
  );
};

export default LogoutButton;
