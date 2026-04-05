import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KZT Digital Twin Dashboard",
  description: "Real-time locomotive health monitoring dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
