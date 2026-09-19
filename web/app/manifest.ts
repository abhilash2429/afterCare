import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AfterCare",
    short_name: "AfterCare",
    description: "Photograph the paper. Check the pill box.",
    start_url: "/",
    display: "standalone",
    background_color: "#f4ede5",
    theme_color: "#f4ede5",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}
