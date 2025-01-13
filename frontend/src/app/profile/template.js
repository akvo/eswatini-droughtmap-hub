import Link from "next/link";
import { LogoutButton } from "@/components";
import { UserContextProvider } from "@/context";
import { auth } from "@/lib";
import { HOME_PAGE } from "@/static/config";

const ProfileTemplate = async ({ children }) => {
  const session = await auth.getSession();
  const role = session?.role || null;
  const homeURL = role ? HOME_PAGE?.[role] : "/";
  return (
    <UserContextProvider>
      <div className="w-full h-screen">
        <div className="w-full py-2 bg-primary">
          <div className="w-full container flex flex-row justify-between items-center">
            <div>
              <Link href={homeURL} className="text-white">
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
