import path from "path";
import { fileURLToPath } from "url";
import CopyPlugin from "copy-webpack-plugin";

/** @type {import('next').NextConfig} */

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const nextConfig = {
  reactStrictMode: true,
  webpack: (config) => {
    config.plugins.push(
      new CopyPlugin({
        patterns: [
          {
            from: "node_modules/leaflet/dist/images",
            to: path.resolve(__dirname, "public", "leaflet", "images"),
          },
          {
            from: path.join(__dirname, "node_modules/tinymce/skins"),
            to: path.join(__dirname, "public/assets/libs/tinymce/skins"),
          },
          {
            from: path.join(__dirname, "node_modules/tinymce/themes"),
            to: path.join(__dirname, "public/assets/libs/tinymce/themes"),
          },
          {
            from: path.join(__dirname, "node_modules/tinymce/icons"),
            to: path.join(__dirname, "public/assets/libs/tinymce/icons"),
          },
          {
            from: path.join(__dirname, "node_modules/tinymce/plugins"),
            to: path.join(__dirname, "public/assets/libs/tinymce/plugins"),
          },
          {
            from: path.join(__dirname, "node_modules/tinymce/models"),
            to: path.join(__dirname, "public/assets/libs/tinymce/models"),
          },
        ],
      })
    );
    return config;
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
      {
        source: '/admin/:path*',
        destination: 'http://localhost:8000/admin/:path*',
      },
    ];
  },
};

export default nextConfig;
