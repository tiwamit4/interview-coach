import type { ReactNode } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  LoaderCircle,
  Sparkles,
} from "lucide-react";
import { ApiError } from "../lib/api";
export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`card ${className}`}>{children}</section>;
}
export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {children}
    </header>
  );
}
export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <div role="alert" className="notice error">
      <AlertCircle size={18} />
      <div>
        {error instanceof Error ? error.message : String(error)}
        {error instanceof ApiError && error.requestId && (
          <small>Reference: {error.requestId}</small>
        )}
      </div>
    </div>
  );
}
export function BusyButton({
  busy,
  children,
  ...props
}: {
  busy?: boolean;
  children: ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      disabled={props.disabled || busy}
      className={`button ${props.className || ""}`}
    >
      {busy ? (
        <LoaderCircle className="spin" size={17} />
      ) : (
        <Sparkles size={17} />
      )}{" "}
      {children}
    </button>
  );
}
export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Sparkles size={24} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
export function Score({
  value,
  label = "Score",
}: {
  value: number;
  label?: string;
}) {
  return (
    <div className="score-block">
      <span className="score-number">
        {value}
        <small>/100</small>
      </span>
      <span>{label}</span>
      <div className="score-track">
        <i style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}
export function Bullets({ items }: { items: string[] }) {
  return items.length ? (
    <ul className="clean-list">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  ) : (
    <p className="muted">None listed.</p>
  );
}
export function Stat({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <Card className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && (
        <small>
          <ArrowUpRight size={13} />
          {detail}
        </small>
      )}
    </Card>
  );
}
