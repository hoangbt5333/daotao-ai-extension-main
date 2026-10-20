import './globals.css';
import type { Metadata } from 'next';
import SidebarWrapper from '../components/SidebarWrapper';

export const metadata: Metadata = {
  title: 'daotao-ai-extension',
  description: 'Web tool hỗ trợ số hóa tài liệu giảng dạy cho daotao.ai',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body style={{ margin: 0 }}>
        <div style={{ display: 'flex' }}>
          <SidebarWrapper />
          <div style={{ flex: 1, padding: 24 }}>{children}</div>
        </div>
      </body>
    </html>
  );
}
