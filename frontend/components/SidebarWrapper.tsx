"use client";
import Sidebar from "./Sidebar";
import { usePathname, useRouter } from "next/navigation";

export default function SidebarWrapper() {
  const router = useRouter();
  const pathname = usePathname();
  const usecase = pathname.split("/")[1] || "create-outline";
  const handleSelect = (key: string) => router.push(`/${key}`);
  return <Sidebar selected={usecase} onSelect={handleSelect} />;
} 