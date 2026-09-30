import { ArrowRight, Check, FileSearch, LoaderCircle, ShieldQuestion, X } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"

import { AppShell } from "../components/AppShell"
import { Button, Chip, ConfidenceBar, EmptyState, LoadingState, PrivacyNote } from "../components/ui"
import { decideDuplicate, getDuplicates, scanDuplicates } from "../lib/api"
import { useFlow } from "../state/useFlow"
import type { Duplicate } from "../types"

export function ReviewPage() {
  const started = useRef(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { updateFlow } = useFlow()
  const [duplicates, setDuplicates] = useState<Duplicate[]>([])
  const [index, setIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const notice = (location.state as { notice?: string } | null)?.notice

  useEffect(() => {
    if (started.current) return
    started.current = true
    async function load() {
      try {
        let items = await getDuplicates()
        if (!items.length) {
          await scanDuplicates()
          items = await getDuplicates()
        }
        setDuplicates(items)
        updateFlow({ reviewStarted: true })
      } catch {
        setError("Duplicate suggestions could not be generated. Confirm mappings for name and date fields first.")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [updateFlow])

  const pending = useMemo(() => duplicates.filter((item) => item.status === "pending"), [duplicates])
  const current = pending[index] || pending[0]
  const reviewed = duplicates.length - pending.length

  async function decide(decision: "confirmed_duplicate" | "not_duplicate") {
    if (!current) return
    setBusy(true)
    setError("")
    try {
      await decideDuplicate(current.id, decision)
      setDuplicates((items) => items.map((item) => item.id === current.id ? { ...item, status: decision } : item))
      setIndex(0)
    } catch {
      setError("The decision could not be saved. Please try again.")
    } finally {
      setBusy(false)
    }
  }

  return <AppShell><main className="page page-fade"><header className="page-heading split-heading"><div><p className="eyebrow">Step 3 of 5</p><h1>{current ? "Possible duplicate" : "Duplicate review"}</h1><p>Compare the evidence behind each suggested match. Traceable never merges records automatically.</p></div>{duplicates.length > 0 && <Chip tone={pending.length ? "warning" : "good"}>{pending.length ? `${reviewed + 1} of ${duplicates.length}` : "Review complete"}</Chip>}</header>{notice && <p className="notice static-notice">{notice}</p>}{error && <p className="inline-error" role="alert">{error}</p>}{loading ? <LoadingState label="Checking records across sources" /> : current ? <><section className="comparison"><RecordCard label="Record A" id={current.left_record_id} /><div className="comparison-mark" aria-hidden="true"><ShieldQuestion size={21} /></div><RecordCard label="Record B" id={current.right_record_id} /></section><section className="match-reasons"><div className="section-title"><div><p className="eyebrow">Why this pair was flagged</p><h2>Per-field similarity</h2></div><strong>{Math.round(current.score * 100)}% overall</strong></div><div className="similarity-list">{Object.entries(current.reasons.field_similarities || {}).map(([field, score]) => <div key={field}><span><strong>{field.replaceAll("_", " ")}</strong><small>{similarityCopy(score)}</small></span><ConfidenceBar value={score} label={`${field} similarity`} /></div>)}</div><PrivacyNote>Personal values remain protected in this review. Similarity signals show why the pair was suggested.</PrivacyNote></section><footer className="decision-bar"><div><p>Is this the same beneficiary?</p><span>Your decision is appended to the audit trail and future training data.</span></div><Button disabled={busy} onClick={() => decide("not_duplicate")}><X size={17} />Keep separate</Button><Button variant="primary" disabled={busy} onClick={() => decide("confirmed_duplicate")}>{busy ? <LoaderCircle className="spin" size={17} /> : <Check size={17} />}Same person</Button></footer></> : <EmptyState title="No more matches to review" text={duplicates.length ? "Every suggested match has a human decision." : "No likely duplicates were found in the confirmed data."} action={<Button variant="primary" onClick={() => navigate("/metrics")}>Continue to metrics <ArrowRight size={17} /></Button>} />}</main></AppShell>
}

function RecordCard({ label, id }: { label: string; id: string }) {
  return <article className="record-card"><header><span><FileSearch size={17} aria-hidden="true" />{label}</span><Chip>Protected raw record</Chip></header><dl><div><dt>Source ID</dt><dd>{id.slice(0, 13)}</dd></div><div><dt>Identity</dt><dd>Pseudonymized for review</dd></div><div><dt>Original</dt><dd>Preserved and unchanged</dd></div></dl></article>
}

function similarityCopy(score: number) {
  if (score >= .9) return "Very close"
  if (score >= .7) return "Likely match"
  if (score >= .45) return "Needs judgment"
  return "Different"
}
