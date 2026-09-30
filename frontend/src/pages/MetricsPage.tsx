import axios from "axios"
import { ArrowRight, BrainCircuit, Check, ChevronDown, LoaderCircle, Pencil, Sparkles, Trash2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"

import { AppShell } from "../components/AppShell"
import { Button, Chip } from "../components/ui"
import { computeMetric, createMetric, getMappings, suggestMetric } from "../lib/api"
import { useFlow } from "../state/useFlow"
import type { Formula, MetricSuggestion } from "../types"

const operations: Formula["operation"][] = ["count", "count_distinct", "sum", "avg", "min", "max"]

export function MetricsPage() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const { updateFlow } = useFlow()
  const [description, setDescription] = useState("")
  const [name, setName] = useState("Unique beneficiaries served")
  const [suggestion, setSuggestion] = useState<MetricSuggestion | null>(null)
  const [schema, setSchema] = useState<string[]>([])
  const [manual, setManual] = useState(false)
  const [editing, setEditing] = useState(false)
  const [technicalOpen, setTechnicalOpen] = useState(false)
  const [specText, setSpecText] = useState("")
  const [manualOperation, setManualOperation] = useState<Formula["operation"]>("count_distinct")
  const [manualField, setManualField] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    getMappings().then((items) => {
      const fields = Array.from(new Set(items.filter((item) => item.status === "confirmed").map((item) => item.canonical_field)))
      setSchema(fields)
      setManualField(fields.find((field) => field.includes("beneficiary")) || fields[0] || "")
    }).catch(() => setManual(true))
  }, [])

  async function draftFormula() {
    if (!description.trim()) return
    setBusy(true)
    setError("")
    try {
      const result = await suggestMetric(description.trim())
      setSuggestion(result)
      setSchema(result.canonical_schema)
      if (result.formula_spec) {
        setSpecText(JSON.stringify(result.formula_spec, null, 2))
        setName(toMetricName(description))
        setManual(false)
      } else {
        inputRef.current?.focus()
      }
    } catch (caught) {
      setManual(true)
      const message = axios.isAxiosError(caught) ? caught.response?.data?.detail?.message : null
      setError(message || "AI drafting is unavailable. Use the manual builder below; it remains fully traceable.")
    } finally {
      setBusy(false)
    }
  }

  async function saveMetric() {
    setBusy(true)
    setError("")
    try {
      let formula: Formula
      if (manual) {
        formula = { operation: manualOperation, field: manualField, filters: [] }
      } else {
        formula = JSON.parse(specText) as Formula
      }
      const created = await createMetric({ name, description: description || `Human-confirmed ${name.toLowerCase()}`, formula, suggestion_id: manual ? undefined : suggestion?.suggestion_id }) as { id: string }
      await computeMetric(created.id)
      updateFlow({ metricCreated: true })
      navigate("/report", { state: { notice: "The metric was human-confirmed, computed, and linked to its source records." } })
    } catch (caught) {
      setError(caught instanceof SyntaxError ? "The technical spec is not valid JSON." : "The metric could not be saved. Check that its fields match confirmed columns.")
    } finally {
      setBusy(false)
    }
  }

  return <AppShell><main className="page page-fade"><header className="page-heading"><p className="eyebrow">Step 4 of 5</p><h1>Define a metric</h1><p>Describe the number you need, then approve the exact calculation before anything is saved.</p></header>{error && <p className="inline-error" role="alert">{error}</p>}<section className="metric-builder"><div className="builder-heading"><span><BrainCircuit size={22} aria-hidden="true" /></span><div><h2>AI-assisted metric draft</h2><p>Assistance only. You remain the approver.</p></div><Chip>Suggestion</Chip></div><label htmlFor="metric-description">Describe the metric in your own words</label><textarea ref={inputRef} id="metric-description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Unique beneficiaries served in the nutrition program in January" /><Button disabled={busy || description.trim().length < 4} onClick={draftFormula}>{busy ? <LoaderCircle className="spin" size={17} /> : <Sparkles size={17} />}Draft formula</Button></section>{suggestion?.clarification_needed && <section className="clarification" role="status"><strong>One detail is needed</strong><p>{suggestion.clarification_needed}</p><Button onClick={() => inputRef.current?.focus()}>Clarify description</Button></section>}{suggestion?.formula_spec && !manual && <section className="suggestion-panel"><header><div><p className="eyebrow">Human review required</p><h2>This will calculate</h2></div><Chip tone="good"><Check size={13} />Ready to review</Chip></header><p className="restatement">{suggestion.restatement}</p><button className="technical-disclosure" onClick={() => setTechnicalOpen((current) => !current)} aria-expanded={technicalOpen}>View technical spec <ChevronDown size={16} /></button>{technicalOpen && (editing ? <textarea className="code-editor" value={specText} onChange={(event) => setSpecText(event.target.value)} aria-label="Editable metric formula JSON" /> : <pre>{specText}</pre>)}<div className="suggestion-actions"><Button variant="text" onClick={() => { setSuggestion(null); setSpecText(""); inputRef.current?.focus() }}><Trash2 size={16} />Discard</Button><Button onClick={() => { setEditing(true); setTechnicalOpen(true) }}><Pencil size={16} />Edit</Button><Button variant="primary" disabled={busy} onClick={saveMetric}>{busy ? <LoaderCircle className="spin" size={17} /> : <Check size={17} />}Save and build report</Button></div></section>}<div className="manual-divider"><span>Manual builder always available</span></div><section className="manual-builder"><header><div><p className="eyebrow">No AI required</p><h2>Build the formula yourself</h2></div><Button onClick={() => setManual((current) => !current)}>{manual ? "Hide manual builder" : "Use manual builder"}</Button></header>{manual && <div className="manual-fields"><label>Metric name<input value={name} onChange={(event) => setName(event.target.value)} /></label><label>Operation<select value={manualOperation} onChange={(event) => setManualOperation(event.target.value as Formula["operation"])}>{operations.map((operation) => <option key={operation} value={operation}>{operation.replaceAll("_", " ")}</option>)}</select></label><label>Field<select value={manualField} onChange={(event) => setManualField(event.target.value)}><option value="">Choose a confirmed field</option>{schema.map((field) => <option key={field} value={field}>{field.replaceAll("_", " ")}</option>)}</select></label><div className="formula-sentence">This will <strong>{manualOperation.replaceAll("_", " ")}</strong> values in <strong>{manualField || "the field you choose"}</strong>. No filters will be applied.</div><Button variant="primary" disabled={busy || !name || !manualField} onClick={saveMetric}>Save and build report <ArrowRight size={17} /></Button></div>}</section></main></AppShell>
}

function toMetricName(description: string) {
  const clean = description.trim().replace(/[.?!]$/, "")
  return clean.charAt(0).toUpperCase() + clean.slice(1, 80)
}
