import "./globals.css";
import { Sidebar } from "../components/Sidebar";
import { Header } from "../components/Header";
import ClientShell from "./ClientShell";

export const metadata = {
  title: "SYRION — Intelligence Platform",
  description: "SYRION Dashboard — Local-First, auditierbar, Phase 1"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body>
        <ClientShell>{children}</ClientShell>
      </body>
    </html>
  );
}
