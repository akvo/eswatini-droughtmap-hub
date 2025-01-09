import localFont from "next/font/local";
import "./globals.css";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { ConfigProvider } from "antd";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata = {
  title: "eSwatini - DroughtMap Hub",
  description:
    "The purpose of the DroughtMap Hub is to provide a user-friendly interface to validate, publish and browse CDI products.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased overflow-hidden`}
      >
        <AntdRegistry>
          <ConfigProvider
            theme={{
              token: {
                borderRadius: 0,
                fontFamily: "inherit",
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
              },
            }}
          >
            {children}
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  );
}
