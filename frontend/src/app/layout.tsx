import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GhostProtocol — NHI Security Dashboard",
  description: "Non-Human Identity auditing and least-privilege enforcement",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
