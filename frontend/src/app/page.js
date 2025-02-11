import { Button, Dropdown } from "antd";
import dynamic from "next/dynamic";
import { auth } from "@/lib";
import Link from "next/link";
import { USER_ROLES } from "@/static/config";
import { LogoutButton } from "@/components";
import { UserCircle } from "@/components/Icons";

const ExampleMap = dynamic(() => import("../components/Map/ExampleMap"), {
  ssr: false,
});

export const Navbar = ({ session = null }) => (
  <div className="w-full py-2 bg-primary">
    <div className="w-full container flex flex-row justify-between items-center">
      <div>
        {session && (
          <Link
            href={
              session?.role === USER_ROLES.admin ? "/publications" : "/reviews"
            }
            className="text-white"
          >
            Dashboard
          </Link>
        )}
      </div>
      <nav className="w-fit px-4">
        {session ? (
          <Dropdown
            placement="bottomRight"
            menu={{
              items: [
                {
                  key: 1,
                  label: (
                    <Link href={"/profile"}>
                      <Button type="link" className="dropdown-item">
                        Profile
                      </Button>
                    </Link>
                  ),
                },
                {
                  key: 2,
                  label: <LogoutButton className="dropdown-item" />,
                },
              ],
            }}
            trigger={["click"]}
            overlayClassName="dropdown-profile"
          >
            <a role="button" className="text-white">
              <UserCircle size={32} />
            </a>
          </Dropdown>
        ) : (
          <Link href={"/login"}>
            <Button type="primary">Login</Button>
          </Link>
        )}
      </nav>
    </div>
  </div>
);

const Home = async () => {
  const session = await auth.getSession();
  return (
    <div className="w-full h-screen">
      <Navbar session={session} />
      <div className="w-full h-full">
        <ExampleMap />
      </div>
    </div>
  );
};

export default Home;
