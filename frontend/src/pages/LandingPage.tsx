import { ArrowRight, FileCheck2, Fingerprint, Link2, ShieldCheck } from "lucide-react"
import { useState } from "react"
import { useNavigate } from "react-router-dom"

import { AppShell } from "../components/AppShell"
import { HowItWorks } from "../components/HowItWorks"
import { Button } from "../components/ui"
import { suggestMappings, uploadFile } from "../lib/api"
import { useFlow } from "../state/useFlow"

export function LandingPage() {
  const navigate = useNavigate()
  const { updateFlow } = useFlow()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function trySampleData() {
    setLoading(true)
    setError("")
    try {
      const files = await Promise.all(["attendance_q3.csv", "workshops_q3.csv"].map(async (name) => {
        const response = await fetch(`/samples/${name}`)
        if (!response.ok) throw new Error("Sample data could not be loaded")
        return new File([await response.blob()], name, { type: "text/csv" })
      }))
      const uploadIds = await Promise.all(files.map(async (file) => {
        const job = await uploadFile(file)
        const uploadId = job.result?.upload_id
        if (!uploadId) throw new Error("The sample upload returned no record ID")
        await suggestMappings(uploadId)
        return uploadId
      }))
      updateFlow({ uploadIds, mappingsConfirmed: false, reviewStarted: false, metricCreated: false })
      navigate("/match", { state: { notice: "Sample files are stored as immutable source records." } })
    } catch (caught) {
      setError(sampleDataError(caught))
    } finally {
      setLoading(false)
    }
  }

  return <AppShell landing><main className="landing-main"><section className="hero"><div className="hero-copy"><p className="eyebrow">Evidence-ready reporting for small nonprofits</p><h1>Reports your funders can trust, from data that started messy.</h1><p className="hero-lede">Turn spreadsheets and attendance records into clear reports where every number links back to its source.</p><div className="hero-actions"><Button variant="primary" onClick={() => navigate("/upload")}>Start a report <ArrowRight size={17} /></Button><Button variant="text" disabled={loading} onClick={trySampleData}>{loading ? "Loading sample data…" : "Try sample data"}</Button></div>{error && <p className="inline-error" role="alert">{error}</p>}<div className="trust-points" id="privacy"><span><FileCheck2 aria-hidden="true" />Nothing overwritten</span><span><Link2 aria-hidden="true" />Every number traced</span><span><ShieldCheck aria-hidden="true" />Names protected</span></div></div><ReportPreview /></section><HowItWorks /></main></AppShell>
}

function sampleDataError(caught: unknown) {
  if (caught instanceof Error && /failed to fetch|network error|econnrefused/i.test(caught.message)) {
    return "The local API is offline. Start the FastAPI server, then try the sample data again."
  }
  return caught instanceof Error ? caught.message : "Sample data could not be loaded"
}

function ReportPreview() {
  return <div className="report-stack" aria-label="Preview of a traceable report"><article className="report-preview"><header><span className="mini-brand"><Fingerprint size={17} />Traceable</span><small>Impact report&nbsp;&nbsp;|&nbsp;&nbsp;Q3 2026</small></header><h2>Q3 program impact</h2><p>A source-linked summary of outcomes and evidence.</p><hr /><strong className="preview-number">412</strong><span className="preview-label">source-linked records</span><div className="preview-kpis"><span><b>3</b>source files</span><span><b>27</b>duplicate decisions</span><span><b>412</b>linked records</span></div><aside><span>!</span>2 records are missing dates</aside><div className="preview-evidence"><strong>Evidence</strong><span>3 files → 27 decisions → 412 records</span></div><table><thead><tr><th>Source file</th><th>Records</th><th>Used</th></tr></thead><tbody><tr><td>Community_Program.csv</td><td>198</td><td>198</td></tr><tr><td>Attendance_Q3.xlsx</td><td>276</td><td>214</td></tr><tr><td>Survey_Results.csv</td><td>64</td><td>0</td></tr></tbody></table></article></div>
}
