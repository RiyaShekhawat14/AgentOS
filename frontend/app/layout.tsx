import { Suspense } from "react";
import "./globals.css";
import Shell from "./(shell)/Shell";

export const metadata = { title: "AgentOS" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Suspense fallback={null}>
          <Shell>{children}</Shell>
        </Suspense>
      </body>
    </html>
  );
}
