import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Alma Lead Intake",
  description: "Lead intake: prospective clients submit their details; an attorney reviews and reaches out.",
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
