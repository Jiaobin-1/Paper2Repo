import "./globals.css";
import { Inter } from "next/font/google";
import NavBar from "./components/shared/NavBar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata = {
  title: "Paper2Repo",
  description: "AI paper understanding and reproduction planning agent.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={inter.variable}>
      <body>
        <NavBar />
        {children}
      </body>
    </html>
  );
}
