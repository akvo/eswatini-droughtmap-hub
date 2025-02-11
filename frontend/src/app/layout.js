import "./globals.css";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { ConfigProvider, Space } from "antd";
import dynamic from "next/dynamic";
import { AppContextProvider } from "@/context";
import { inter, roboto, robotoMono } from "./fonts";
import classNames from "classnames";
import Image from "next/image";
import dayjs from "dayjs";
import { APP_SETTINGS } from "@/static/config";

export const metadata = {
  title: "eSwatini - DroughtMap Hub",
  description:
    "The purpose of the DroughtMap Hub is to provide a user-friendly interface to validate, publish and browse SPI products.",
};

const DynamicScript = dynamic(() => import("@/components/DynamicScript"), {
  ssr: false,
});

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body
        className={classNames(
          "antialiased",
          inter.variable,
          roboto.variable,
          robotoMono.variable
        )}
      >
        <AppContextProvider>
          <AntdRegistry>
            <ConfigProvider
              theme={{
                token: {
                  borderRadius: 0,
                  fontFamily: "inherit",
                  fontFamilyCode: "--font-geist-sans",
                  colorPrimary: "#3E5EB9",
                  colorLink: "#3E5EB9",
                },
                components: {
                  Form: {
                    itemMarginBottom: 16,
                  },
                  Tabs: {
                    inkBarColor: "#3E5EB9",
                    itemActiveColor: "#3E5EB9",
                    itemColor: "#3E4958",
                    itemHoverColor: "#3E4958",
                    itemSelectedColor: "#3E5EB9",
                    titleFontSize: 16,
                    titleFontSizeLG: 20,
                    titleFontSizeSM: 16,
                  },
                  Table: {
                    cellPaddingInline: 8,
                    cellPaddingBlock: 4,
                  },
                  Descriptions: {
                    labelBg: "#f1f5f9",
                    titleColor: "#020618",
                  },
                },
              }}
            >
              {children}
              <footer className="w-full px-0 py-6 bg-primary">
                <div className="container w-full text-white text-base flex flex-row items-center justify-between">
                  <div>
                    <p>
                      &copy; {dayjs().format("YYYY")} - {APP_SETTINGS.copy}
                    </p>
                  </div>
                  <div>
                    <a href="https://akvo.org/" target="_blank">
                      <Space size="middle">
                        <p>Powered by </p>
                        <Image
                          src="/images/logo-akvo.png"
                          alt="Akvo Foundation Logo"
                          width={64}
                          height={24}
                        />
                      </Space>
                    </a>
                  </div>
                </div>
              </footer>
            </ConfigProvider>
          </AntdRegistry>
          <div suppressHydrationWarning>
            <DynamicScript />
          </div>
        </AppContextProvider>
      </body>
    </html>
  );
}
