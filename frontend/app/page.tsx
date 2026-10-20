"use client";
import React from "react";
import { useRouter, usePathname } from "next/navigation";
import Sidebar from "../components/Sidebar";

export default function HomeLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  // Xác định usecase từ pathname
  const usecase = pathname.split("/")[1] || "create-outline";

  const handleSelect = (key: string) => {
    router.push(`/${key}`);
  };

  return (
    <div style={{ display: "flex" }}>
      <Sidebar selected={usecase} onSelect={handleSelect} />
      <div style={{ flex: 1, padding: 24 }}>{children}</div>
    </div>
  );
}
