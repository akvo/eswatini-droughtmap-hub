import Link from "next/link";
import { LogoutButton } from "@/components";
import { UserContextProvider } from "@/context";

const ProfileTemplate = ({ children }) => {
  return (
    <UserContextProvider>
      <div className="w-full h-screen">
        <div className="w-full py-2 bg-primary">
          <div className="w-full container flex flex-row justify-between items-center">
            <div>
              <Link href={"/"} className="text-white">
                Home
              </Link>
            </div>
            <div>
              <LogoutButton />
            </div>
          </div>
        </div>
        <div className="w-full container">{children}</div>
      </div>
    </UserContextProvider>
  );
};

export default ProfileTemplate;
