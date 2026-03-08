import type { Metadata } from "next";
import "./globals.css";
import ToastContainer from "@/components/Toast";

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
      <body className="antialiased">
        {children}
        <ToastContainer />
      </body>
    </html>
  );
}
