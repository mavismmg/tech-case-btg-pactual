import type { ReactNode } from "react";

export function Panel({ title, actions, children }: { title: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
        {actions ? <div className="panel-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function Stat({ label, value, detail }: { label: string; value: string | number; detail?: string }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}
