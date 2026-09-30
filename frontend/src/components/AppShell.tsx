import { Moon, Sun } from "lucide-react"
import { useEffect, useState, type ReactNode } from "react"
import { Link, useLocation } from "react-router-dom"

const steps = [
  { label: "Upload", path: "/upload" },
  { label: "Match", path: "/match" },
  { label: "Review", path: "/review" },
  { label: "Metrics", path: "/metrics" },
  { label: "Report", path: "/report" },
]

function Brand() {
  return <Link className="brand" to="/" aria-label="Traceable home"><span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span><span>Traceable</span></Link>
}

function StepTracker() {
  const location = useLocation()
  const current = steps.findIndex((step) => location.pathname.startsWith(step.path))
  return <nav className="step-tracker" aria-label="Report progress">{steps.map((step, index) => <span className={index === current ? "current" : index < current ? "done" : "upcoming"} key={step.path}><i aria-hidden="true" />{step.label}</span>)}</nav>
}

export function AppShell({ children, landing = false }: { children: ReactNode; landing?: boolean }) {
  const [theme, setTheme] = useState(() => window.localStorage.getItem("traceable-theme") || "light")

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem("traceable-theme", theme)
  }, [theme])

  return <div className={`app-shell ${landing ? "landing-shell" : ""}`}><header className="site-header"><Brand />{landing ? <nav className="landing-nav" aria-label="Main navigation"><a href="#how-it-works">How it works</a><a href="#privacy">Privacy</a><Link className="button button-primary" to="/upload">Start a report</Link></nav> : <StepTracker />}<button className="theme-toggle" onClick={() => setTheme((current) => current === "dark" ? "light" : "dark")} aria-label={`Use ${theme === "dark" ? "light" : "dark"} theme`}>{theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}</button></header>{children}</div>
}
