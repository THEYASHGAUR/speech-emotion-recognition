"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  History,
  LogOut,
  Waves,
  ChevronRight,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/upload", icon: Upload, label: "Upload File" },
  { href: "/history", icon: History, label: "History" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    localStorage.removeItem("autoace_token");
    localStorage.removeItem("autoace_username");
    router.push("/login");
  }

  const username =
    typeof window !== "undefined"
      ? localStorage.getItem("autoace_username") || "admin"
      : "admin";

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div style={{ marginBottom: "32px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "0 4px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 4px 12px rgba(79,70,229,0.25)",
              flexShrink: 0,
            }}
          >
            <Waves size={18} color="white" />
          </div>
          <div>
            <div style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-primary)", lineHeight: "1" }}>
              AutoAce
            </div>
            <div style={{ fontSize: "10px", color: "var(--accent)", fontWeight: "600", letterSpacing: "0.05em", textTransform: "uppercase" }}>
              AI Platform
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ display: "flex", flexDirection: "column", gap: "4px", flex: 1 }}>
        <div style={{ fontSize: "10px", fontWeight: "600", color: "var(--text-muted)", letterSpacing: "0.1em", textTransform: "uppercase", padding: "0 14px", marginBottom: "8px" }}>
          Main Menu
        </div>
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
          const isActive = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`nav-item ${isActive ? "active" : ""}`}
            >
              <Icon size={16} />
              <span style={{ flex: 1 }}>{label}</span>
              {isActive && <ChevronRight size={14} style={{ opacity: 0.5 }} />}
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      <div
        style={{
          borderTop: "1px solid var(--border)",
          paddingTop: "16px",
          marginTop: "16px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "10px 14px",
            borderRadius: "10px",
            background: "#f8fafc",
            border: "1px solid var(--border)",
            marginBottom: "8px",
          }}
        >
          <div
            style={{
              width: "30px",
              height: "30px",
              background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "12px",
              fontWeight: "700",
              color: "white",
              flexShrink: 0,
            }}
          >
            {username.charAt(0).toUpperCase()}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {username}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Administrator</div>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="nav-item"
          style={{ width: "100%", background: "none", border: "none", cursor: "pointer", color: "#dc2626" }}
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
