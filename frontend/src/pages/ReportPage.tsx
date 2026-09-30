import { ChevronLeft, ChevronRight, Database, Download, FileCheck2, Files, Link2, Pencil, Search, Table2, Users, X } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"

import { AppShell } from "../components/AppShell"
import { MetricsSunburst } from "../components/MetricsSunburst"
import { Button, DataGapCallout, EmptyState, LoadingState, PrivacyNote } from "../components/ui"
import { getReport, getSharedReport } from "../lib/api"
import type { Metric, Report, SourceRecord } from "../types"

const pageSize = 5

export function ReportPage({ shared = false }: { shared?: boolean }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { token } = useParams()
  const [report, setReport] = useState<Report | null>(null)
  const [selectedMetric, setSelectedMetric] = useState(0)
  const [selectedRecord, setSelectedRecord] = useState<SourceRecord | null>(null)
  const [title, setTitle] = useState("Q3 program impact")
  const [editingTitle, setEditingTitle] = useState(false)
  const [query, setQuery] = useState("")
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const notice = (location.state as { notice?: string } | null)?.notice

  useEffect(() => {
    const request = shared && token ? getSharedReport(token) : getReport()
    request.then((data) => { setReport(data); setTitle(data.title || "Q3 program impact") }).catch(() => setError(shared ? "This shared report is unavailable." : "The report could not be loaded from the API.")).finally(() => setLoading(false))
  }, [shared, token])

  const metric = report?.metrics[selectedMetric]
  const records = useMemo(() => {
    if (!report || !metric) return []
    const ids = new Set(metric.source_record_ids)
    return report.contributing_records.filter((record) => ids.has(record.source_record_id) && JSON.stringify(record).toLowerCase().includes(query.toLowerCase()))
  }, [metric, query, report])
  const pageCount = Math.max(1, Math.ceil(records.length / pageSize))
  const visibleRecords = records.slice(page * pageSize, page * pageSize + pageSize)
  const gaps = useMemo(() => {
    if (!report) return []
    const structured = report.data_gaps.map((gap) => ({ label: gap.label, count: gap.count }))
    const caveats = metric?.caveats.map((label) => ({ label })) || []
    return [...structured, ...caveats]
  }, [metric, report])

  function selectMetric(index: number) {
    setSelectedMetric(index)
    setSelectedRecord(null)
    setQuery("")
    setPage(0)
  }

  if (loading) return <AppShell><main className="page"><LoadingState label="Building source-linked report" /></main></AppShell>
  if (error || !report) return <AppShell><main className="page"><p className="inline-error" role="alert">{error}</p></main></AppShell>
  if (!metric) return <AppShell><main className="page"><EmptyState title="No computed metric yet" text="Confirm and compute a metric before opening the report." action={<Button variant="primary" onClick={() => navigate("/metrics")}>Define a metric</Button>} /></main></AppShell>

  return <AppShell><main className="page report-page page-fade"><header className="report-header"><div><p className="eyebrow">Report</p><div className="editable-title">{editingTitle && !shared ? <input value={title} onChange={(event) => setTitle(event.target.value)} onBlur={() => setEditingTitle(false)} autoFocus aria-label="Report title" /> : <h1>{title}</h1>}{!shared && <button onClick={() => setEditingTitle(true)} aria-label="Edit report title"><Pencil size={17} /></button>}</div><p>Generated {new Date(report.generated_at).toLocaleDateString()} · source-linked evidence</p></div>{!shared && <div className="report-actions"><Button onClick={() => navigator.clipboard.writeText(window.location.href)}><Link2 size={17} />Copy link</Button><a className="button button-primary" href="/api/report.pdf"><Download size={17} />Export PDF</a></div>}</header>{notice && <p className="notice static-notice">{notice}</p>}<article className="report-dossier"><section className="report-lead"><div className="headline-metric"><label htmlFor="metric-select">Metric</label><select id="metric-select" value={selectedMetric} onChange={(event) => selectMetric(Number(event.target.value))}>{report.metrics.map((item, index) => <option value={index} key={item.id}>{item.name}</option>)}</select><strong>{formatValue(metric.value)}</strong><p>{metric.description || readableFormula(metric)}</p><button onClick={() => document.getElementById("source-records")?.scrollIntoView({ behavior: "smooth" })}>View source records <ChevronRight size={16} /></button></div><LineageChain report={report} metric={metric} /></section><MetricsSunburst metrics={report.metrics} records={report.contributing_records} selectedIndex={selectedMetric} onSelect={selectMetric} /><DataGapCallout gaps={gaps} /><section className="kpi-strip"><Kpi value={new Set(report.contributing_records.map((record) => record.source.split(" · ")[0])).size} label="Source files" detail="Data combined from immutable uploads" /><Kpi value={report.lineage?.nodes.filter((node) => node.type === "mapping").length || 0} label="Columns confirmed" detail="Only human-approved mappings" /><Kpi value={metric.source_record_ids.length} label="Source-linked records" detail="Exact records behind this number" /></section><section className="records-section" id="source-records"><header><div><h2>Source records</h2><PrivacyNote>Names are pseudonymized. Showing {visibleRecords.length} of {records.length} source records.</PrivacyNote></div><div className="record-tools"><label className="search-field"><Search size={16} aria-hidden="true" /><span className="visually-hidden">Search source records</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(0) }} placeholder="Search source ID, beneficiary or program" /></label><div className="pagination"><Button aria-label="Previous page" disabled={page === 0} onClick={() => setPage((current) => current - 1)}><ChevronLeft size={16} /></Button><span>{page + 1} of {pageCount}</span><Button aria-label="Next page" disabled={page + 1 >= pageCount} onClick={() => setPage((current) => current + 1)}><ChevronRight size={16} /></Button></div></div></header><div className="source-layout"><div className="table-scroll"><table className="source-table"><thead><tr><th>Source ID</th><th>File and row</th><th>Beneficiary</th><th>Program</th><th>Date</th></tr></thead><tbody>{visibleRecords.map((record) => <tr key={record.source_record_id} className={selectedRecord?.source_record_id === record.source_record_id ? "selected" : ""} onClick={() => setSelectedRecord(record)}><td><button>{shortSourceId(record.source_record_id)}</button></td><td>{record.source}</td><td>{record.pseudonym}</td><td>{String(record.values.program || record.values.activity || "—")}</td><td>{String(record.values.event_date || record.values.date || "Missing")}</td></tr>)}{!visibleRecords.length && <tr><td colSpan={5}>No source records match this search.</td></tr>}</tbody></table></div>{selectedRecord && <RecordDrawer record={selectedRecord} close={() => setSelectedRecord(null)} />}</div></section></article><footer className="report-footer"><strong>Traceable</strong><span>Verifiable people. Stronger programs.</span><span>{title} · {new Date(report.generated_at).toLocaleDateString()}</span></footer></main></AppShell>
}

function LineageChain({ report, metric }: { report: Report; metric: Metric }) {
  const files = new Set(report.contributing_records.map((record) => record.source.split(" · ")[0])).size
  const mappings = report.lineage?.nodes.filter((node) => node.type === "mapping").length || 0
  const decisions = report.audit_trail.filter((event) => event.entity_type === "duplicate_candidate").length
  const items = [{ icon: Files, value: files, label: "source files" }, { icon: Table2, value: mappings, label: "columns confirmed" }, { icon: Users, value: decisions, label: "duplicate decisions" }, { icon: Database, value: metric.source_record_ids.length, label: "source-linked records" }]
  return <div className="lineage-chain" aria-label="Data lineage">{items.map((item) => <div key={item.label}><span><item.icon size={22} aria-hidden="true" /></span><strong>{item.value}</strong><small>{item.label}</small></div>)}</div>
}

function Kpi({ value, label, detail }: { value: number; label: string; detail: string }) {
  return <div><strong>{value}</strong><span><b>{label}</b><small>{detail}</small></span></div>
}

function RecordDrawer({ record, close }: { record: SourceRecord; close: () => void }) {
  return <aside className="record-drawer"><header><span><FileCheck2 size={18} />{shortSourceId(record.source_record_id)}</span><button onClick={close} aria-label="Close source record details"><X size={18} /></button></header><p>Source record details</p><dl><div><dt>Beneficiary</dt><dd>{record.pseudonym}</dd></div>{Object.entries(record.values).slice(0, 7).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{String(value || "Missing")}</dd></div>)}<div><dt>Source file</dt><dd>{record.source}</dd></div></dl><PrivacyNote>The original identity mapping is separate and access-controlled.</PrivacyNote></aside>
}

function formatValue(value: number) {
  return new Intl.NumberFormat().format(value)
}

function shortSourceId(id: string) {
  return `SRC-${id.replaceAll("-", "").slice(0, 6).toUpperCase()}`
}

function readableFormula(metric: Metric) {
  return `${metric.formula.operation.replaceAll("_", " ")} of ${metric.formula.field?.replaceAll("_", " ") || "records"}, with every contributing row attached.`
}
