import Link from "next/link";
import { Button, Flex, Space } from "antd";
import { UserContextProvider } from "@/context";
import { auth } from "@/lib";

const ReviewLayout = async ({ children }) => {
  const session = await auth.getSession();
  const abilities = session?.abilities || [];
  return (
    <UserContextProvider abilities={abilities}>
      <div className="w-full max-w-9xl h-screen relative text-base text-dark-10 overflow-hidden">
        <div className="w-full flex items-center bg-primary py-2 sticky top-0 z-50">
          <div className="container mx-auto">
            <Flex className="w-full" justify="space-between" align="center">
              <Space>
                <Link href={"/"} className="text-white">
                  Home
                </Link>
                <Link href={"/reviews"} className="text-white">
                  Dashboard
                </Link>
              </Space>
              <div>
                <Link href={"/profile"}>
                  <Button>Profile</Button>
                </Link>
              </div>
            </Flex>
          </div>
        </div>
        <main className="w-full flex items-center relative">
          <div className="container mx-auto">{children}</div>
        </main>
      </div>
    </UserContextProvider>
  );
};

export default ReviewLayout;
