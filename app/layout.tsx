import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL("https://ir-spoke-link-sim.niklasdat.chatgpt.site"),
  title: "IR Spoke Sensor - Live System Model",
  description: "Interactive optical, analog and RMT model for the IR spoke sensor.",
  openGraph: {
    title: "IR Spoke Sensor",
    description: "Variable-carrier optical, analog and ESP32-S3 RMT model.",
    images: [{ url: "/og.png", width: 1728, height: 910 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "IR Spoke Sensor",
    description: "Variable-carrier optical, analog and ESP32-S3 RMT model.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body
    className={`${geistSans.variable} ${geistMono.variable}`}>
    {children}
  </body></html>;
}
