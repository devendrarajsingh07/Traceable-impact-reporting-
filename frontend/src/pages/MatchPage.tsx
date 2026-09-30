import { ArrowRight, Check, LoaderCircle } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"

import { AppShell } from "../components/AppShell"
import { Button, Chip, ConfidenceBar, EmptyState, LoadingState } from "../components/ui"
import { confirmMapping, getMappings } from "../lib/api"
import { useFlow } from "../state/useFlow"
import type { Mapping } from "../types"

const commonFields = ["beneficiary_id", "beneficiary_name", "program", "event_date", "status", "location", "amount"]

export function MatchPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { updateFlow } = useFlow()
  const [mappings, setMappings] = useState<Mapping[]>([])
  const [selections, setSelections] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const notice = (location.state as { notice?: string } | null)?.notice

  useEffect(() => {
    getMappings().then((items) => {
      setMappings(items)
      setSelections(Object.fromEntries(items.map((item) => [item.id, item.status === "confirmed" || item.confidence >= .7 ? item.canonical_field : ""])))
    }).catch(() => setError("Column suggestions could not be loaded.")).finally(() => setLoading(false))
  }, [])

  const fields = useMemo(() => Array.from(new Set([...commonFields, ...mappings.map((item) => item.canonical_field)])).sort(), [mappings])
  const complete = mappings.length > 0 && mappings.every((item) => item.status === "confirmed" || Boolean(selections[item.id]))

  async function confirmAll() {
    if (!complete) return
    setBusy(true)
    setError("")
    try {
      await Promise.all(mappings.filter((item) => item.status !== "confirmed" || selections[item.id] !== item.canonical_field).map((item) => confirmMapping(item.id, selections[item.id])))
      const confirmed = await getMappings()
      setMappings(confirmed)
      updateFlow({ mappingsConfirmed: true })
      navigate("/review", { state: { notice: `${confirmed.length} column decisions were added to the audit trail.` } })
    } catch {
      setError("One or more mappings could not be confirmed. Review each selected field and try again.")
    } finally {
      setBusy(false)
    }
  }

  return <AppShell><main className="page page-fade"><header className="page-heading"><p className="eyebrow">Step 2 of 5</p><h1>Match your columns</h1><p>Review each suggestion before it can be used in a calculation. Low-confidence matches wait for your choice.</p></header>{notice && <p className="notice static-notice">{notice}</p>}{error && <p className="inline-error" role="alert">{error}</p>}{loading ? <LoadingState label="Finding likely column matches" /> : mappings.length ? <section className="mapping-card"><div className="table-scroll"><table className="mapping-table"><thead><tr><th>Your column</th><th>Maps to</th><th>Confidence</th><th>Status</th></tr></thead><tbody>{mappings.map((item) => { const confidence = item.confidence >= .7; const selected = selections[item.id] || ""; return <tr key={item.id}><td><strong>{item.raw_column}</strong><small>Source upload {item.upload_id.slice(0, 8)}</small></td><td><label className="visually-hidden" htmlFor={`mapping-${item.id}`}>Canonical field for {item.raw_column}</label><select id={`mapping-${item.id}`} value={selected} onChange={(event) => setSelections((current) => ({ ...current, [item.id]: event.target.value }))} disabled={item.status === "confirmed"}><option value="">Choose a field</option>{fields.map((field) => <option key={field} value={field}>{field.replaceAll("_", " ")}</option>)}</select>{selected && selected !== item.canonical_field && <small>Override will be logged</small>}</td><td><ConfidenceBar value={item.confidence} label={`${item.raw_column} match confidence`} /></td><td>{item.status === "confirmed" ? <Chip tone="good">Confirmed</Chip> : <Chip tone={confidence ? "good" : "warning"}>{confidence ? "Good suggestion" : "Check required"}</Chip>}</td></tr> })}</tbody></table></div><div className="mapping-summary"><Check size={17} aria-hidden="true" /><span>{mappings.filter((item) => item.status === "confirmed").length} of {mappings.length} already confirmed</span></div></section> : <EmptyState title="No columns to match" text="Upload a source file first so Traceable can suggest mappings." action={<Button onClick={() => navigate("/upload")}>Return to upload</Button>} />}<footer className="page-actions"><p>Nothing is applied until you confirm every row.</p><Button variant="primary" disabled={!complete || busy} onClick={confirmAll}>{busy ? <LoaderCircle className="spin" size={17} /> : null}{busy ? "Confirming…" : "Confirm mapping"}<ArrowRight size={17} /></Button></footer></main></AppShell>
}
