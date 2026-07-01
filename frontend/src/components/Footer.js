"use client";

import { Button, Input } from "antd";
import Image from "next/image";
import Link from "next/link";
import dayjs from "dayjs";
import { APP_SETTINGS, FOOTER_LINK_COLUMNS } from "@/static/config";
import { usePathname } from "next/navigation";

const Footer = () => {
  const pathname = usePathname();
  if (pathname === "/iframe/map") {
    return null;
  }
  return (
    <footer className="w-full bg-white border-t border-t-neutral-300 flex flex-col items-center gap-16 pt-16">
      <div className="container w-full flex flex-col gap-10 lg:flex-row lg:justify-between">
        <p className="w-full lg:w-80 text-base text-[#606060]">
          {APP_SETTINGS.about}
        </p>

        <div className="flex flex-col gap-8 md:flex-row">
          <div className="flex gap-8">
            {FOOTER_LINK_COLUMNS.map((col) => (
              <div key={col.title} className="flex flex-col gap-4 w-40">
                <p className="text-sm font-medium text-[#333333]">
                  {col.title}
                </p>
                <div className="flex flex-col gap-3">
                  {col.links.map((l) => (
                    <Link
                      key={l.label}
                      href={l.url}
                      className="text-sm text-brandMuted hover:text-[#465d91]"
                    >
                      {l.label}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* ponytail: presentational — no newsletter endpoint yet */}
          <div className="w-full md:w-80 flex flex-col gap-1.5">
            <label className="text-sm text-[#333333]">Stay up to date</label>
            <div className="flex gap-4 items-center">
              <Input type="email" placeholder="Enter your email" />
              <Button type="primary">Subscribe</Button>
            </div>
          </div>
        </div>
      </div>

      <div className="w-full bg-primary">
        <div className="container w-full py-10 flex flex-row items-center justify-between gap-4 text-white text-sm">
          <p>
            &copy; {dayjs().format("YYYY")} - {APP_SETTINGS.copy}
          </p>
          <a
            href="https://akvo.org/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-row items-center gap-4"
          >
            <span>Powered by</span>
            <Image
              src="/images/logo-akvo.png"
              alt="Akvo Foundation Logo"
              width={64}
              height={24}
            />
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
