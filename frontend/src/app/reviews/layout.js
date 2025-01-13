import Link from "next/link";
import { Button } from "antd";
import { UserContextProvider } from "@/context";
import { auth } from "@/lib";

const ReviewLayout = async ({ children }) => {
  const session = await auth.getSession();
  const abilities = session?.abilities || [];
  return (
    <UserContextProvider abilities={abilities}>
      <div className="w-full h-screen">
        <div className="w-full py-2 bg-primary">
          <div className="w-full container flex flex-row justify-between items-center">
            <div>
              <Link href={"/reviews"} className="text-white">
                Home
              </Link>
            </div>
            <div>
              <Link href={"/profile"}>
                <Button>Profile</Button>
              </Link>
            </div>
          </div>
        </div>
        <div className="w-full container">{children}</div>
      </div>
    </UserContextProvider>
  );
};

export default ReviewLayout;
