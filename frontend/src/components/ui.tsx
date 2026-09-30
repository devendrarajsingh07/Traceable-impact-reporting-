import { AlertTriangle, Check, ChevronRight, FileText, LockKeyhole } from "lucide-react"
import type { ButtonHTMLAttributes, ReactNode } from "react"

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`card ${className}`.trim()}>{children}</section>
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "text"
}

export function Button({ variant = "secondary", className = "", children, ...props }: ButtonProps) {
  return <button className={`button button-${variant} ${className}`.trim()} {...props}>{children}</button>
}

export function Chip({ tone = "neutral", children }: { tone?: "neutral" | "good" | "warning"; children: ReactNode }) {
  return <span className={`chip chip-${tone}`}>{tone === "good" && <Check size={13} aria-hidden="true" />}{children}</span>
}

export function ConfidenceBar({ value, label }: { value: number; label?: string }) {
  const percent = Math.round(Math.max(0, Math.min(1, value)) * 100)
  return <div className="confidence" aria-label={label ? `${label}: ${percent}%` : `${percent}% confidence`}><div className="confidence-track"><span style={{ "--progress": `${percent}%` } as React.CSSProperties} /></div><b>{percent}%</b></div>
}

export function DataGapCallout({ gaps }: { gaps: Array<{ label: string; count?: number }> }) {
  return <aside className="data-gap-callout"><AlertTriangle size={21} aria-hidden="true" /><strong>Data gaps and assumptions</strong><div>{gaps.length ? gaps.map((gap, index) => <span key={`${gap.label}-${index}`}>{gap.count ? `${gap.count} ` : ""}{gap.label}</span>) : <span>No unresolved gaps for this report.</span>}</div><ChevronRight size={20} aria-hidden="true" /></aside>
}

export function EmptyState({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return <div className="empty-state"><span><FileText size={24} aria-hidden="true" /></span><h2>{title}</h2><p>{text}</p>{action}</div>
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return <div className="loading-state" role="status"><span className="spinner" /><span>{label}</span></div>
}

export function PrivacyNote({ children }: { children: ReactNode }) {
  return <p className="privacy-note"><LockKeyhole size={14} aria-hidden="true" />{children}</p>
}
