import type { ReactNode } from "react";

export { formatDate } from "../utils/formatters";

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "good" | "warn" | "bad" | "neutral" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "error" | "success" }) {
  return (
    <div className={`notice ${tone}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}
