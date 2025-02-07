"use client";

import Link from "next/link";
import { Button, Dropdown } from "antd";
import { UserCircle } from "./Icons";
import { LogoutButton } from "./Buttons";
import { USER_ROLES } from "@/static/config";

const DashboardLayout = ({ user, children }) => {
  return (
    <div className="w-full h-screen">
      <div className="w-full py-2 bg-primary sticky top-0 z-50">
        <div className="w-full container flex flex-row justify-between items-center">
          <div>
            <Link
              href={
                user?.role === USER_ROLES.admin ? "/publications" : "/reviews"
              }
              className="text-white"
            >
              Dashboard
            </Link>
          </div>
          <div>
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
              <a
                role="button"
                className="text-white"
                onClick={(e) => e.preventDefault()}
              >
                <UserCircle size={32} />
              </a>
            </Dropdown>
          </div>
        </div>
      </div>
      <main className="w-full container">{children}</main>
    </div>
  );
};

export default DashboardLayout;
