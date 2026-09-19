import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const dir = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  transpilePackages: [
    "aws-amplify",
    "@aws-amplify/auth",
    "@aws-amplify/core",
  ],
  turbopack: {
    root: dir,
  },
};

export default nextConfig;
