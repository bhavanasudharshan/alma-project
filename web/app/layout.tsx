import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Alma Lead Intake",
  description: "Immigration lead intake and assessment",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
