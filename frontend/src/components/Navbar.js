"use client";

import { getProfileDropdownItems } from "@/lib";
import { Button, Dropdown } from "antd";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserCircle, WarningCicle } from "./Icons";
import classNames from "classnames";
import { APP_SETTINGS, PUBLIC_MENU_ITEMS, USER_ROLES } from "@/static/config";
import { LogoutButton } from "./Buttons";

const NavItem = ({ pathname, url, label }) => {
  return (
    <Link
      href={url}
      className={classNames(
        "inline-flex items-center h-[69px] px-4 text-white font-semibold text-xs transition-colors duration-300",
        {
          "bg-navActive": pathname === url,
          "hover:bg-navHover": pathname !== url,
        },
      )}
    >
      {label}
    </Link>
  );
};

const Navbar = ({ session }) => {
  const pathname = usePathname();
  const profileItems = getProfileDropdownItems(session, true);
  const menuItems = PUBLIC_MENU_ITEMS.filter(
    (m) => !m.authenticated || session,
  );
  const leftItems = menuItems.filter((m) => m.align !== "right");
  const rightItems = menuItems.filter((m) => m.align === "right");

  return (
    <header className="w-full">
      {/* Notice bar */}
      <div className="w-full bg-neutral-200">
        <div className="container w-full flex flex-row items-center justify-between py-2 text-neutral-600">
          <div className="flex flex-row items-center gap-1.5 text-xs">
            <WarningCicle size={16} />
            <span>{APP_SETTINGS.notice}</span>
          </div>
          <Link href="/feedback" className="text-sm text-neutral-600">
            Contact us
          </Link>
        </div>
      </div>

      {/* Header navigation */}
      <div className="w-full bg-primary">
        <div className="container w-full flex flex-row items-center justify-between">
          <nav className="flex flex-row items-center text-base">
            {leftItems
              .filter(
                (m) =>
                  m?.is_admin === (session?.role === USER_ROLES.admin) ||
                  typeof m?.is_admin === "undefined",
              )
              .map((m, mx) => (
                <NavItem {...m} pathname={pathname} key={mx} />
              ))}
          </nav>

          <div className="flex flex-row items-center gap-4">
            <nav className="flex flex-row items-center text-base">
              {rightItems
                .filter(
                  (m) =>
                    m?.is_admin === (session?.role === USER_ROLES.admin) ||
                    typeof m?.is_admin === "undefined",
                )
                .map((m, mx) => (
                  <NavItem {...m} pathname={pathname} key={mx} />
                ))}
            </nav>
            {session ? (
              <Dropdown
                placement="bottomRight"
                menu={{
                  items: [
                    ...profileItems,
                    {
                      key: 99,
                      label: <LogoutButton className="dropdown-item" />,
                    },
                  ],
                }}
                trigger={["click"]}
                overlayClassName="dropdown-profile"
              >
                <a role="button" className="text-white" aria-label="Profile">
                  <UserCircle size={32} />
                </a>
              </Dropdown>
            ) : (
              <Link href={"/login"}>
                <Button ghost>Login</Button>
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
