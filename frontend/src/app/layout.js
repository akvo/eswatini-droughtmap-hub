import "./globals.css";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { ConfigProvider } from "antd";
import dynamic from "next/dynamic";
import { AppContextProvider } from "@/context";
import { inter, roboto, robotoMono } from "./fonts";
import classNames from "classnames";
import { Footer, LogoSection, Navbar } from "@/components";
import antTheme from "@/static/ant-theme";
import { auth } from "@/lib";

export const metadata = {
  title: "eSwatini - DroughtMap Hub",
  description:
    "The purpose of the DroughtMap Hub is to provide a user-friendly interface to validate, publish and browse CDI products.",
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
              <div className="w-full min-h-screen bg-image-login bg-no-repeat bg-center bg-cover flex flex-col">
                <Navbar session={session} />
                <div className="container w-full h-full relative space-y-4 xl:space-y-8 pt-3 pb-9 bg-white">
                  {children}
                </div>
                <LogoSection />
              </div>
              <Footer />
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
