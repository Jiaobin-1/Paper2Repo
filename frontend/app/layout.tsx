import "./globals.css";

export const metadata = {
  title: "Paper2Repo",
  description: "AI paper understanding and reproduction planning agent.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
