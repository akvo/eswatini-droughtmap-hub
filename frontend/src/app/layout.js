import "./globals.css";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { ConfigProvider } from "antd";
import dynamic from "next/dynamic";
import { AppContextProvider } from "@/context";
import { inter, roboto, robotoMono } from "./fonts";
import classNames from "classnames";
import AppShell from "@/components/AppShell";
import antTheme from "@/static/ant-theme";
import { auth } from "@/lib";

export const metadata = {
  title: "Eswatini Drought Intelligence Hub",
  description:
    "The Eswatini Drought Intelligence Hub is a platform that provides information and resources related to drought conditions in Eswatini. It aims to support decision-making and response efforts by offering data, analysis, and tools for stakeholders.",
};

const DynamicScript = dynamic(() => import("@/components/DynamicScript"), {
  ssr: false,
});

const RootLayout = async ({ children }) => {
  const session = await auth.getSession();

  return (
    <html lang="en">
      <body
        className={classNames(
          "antialiased",
          inter.variable,
          roboto.variable,
          robotoMono.variable,
        )}
      >
        <AppContextProvider>
          <AntdRegistry>
            <ConfigProvider theme={antTheme}>
              <AppShell session={session}>{children}</AppShell>
            </ConfigProvider>
          </AntdRegistry>
          <div suppressHydrationWarning>
            <DynamicScript />
          </div>
        </AppContextProvider>
      </body>
    </html>
  );
};

export default RootLayout;
