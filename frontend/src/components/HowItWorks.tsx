import { Check, Columns3, FileCheck2, FileUp, Fingerprint, ScanSearch, Sigma } from "lucide-react"
import { useState } from "react"
import type { KeyboardEvent } from "react"

const workflowSteps = [
  {
    id: "add-files",
    label: "Add files",
    eyebrow: "Immutable intake",
    title: "Preserve the original evidence",
    description: "Upload CSV or Excel files. Every source row receives its own ID and stays exactly as submitted.",
    icon: FileUp,
    scene: "files",
  },
  {
    id: "match-columns",
    label: "Match columns",
    eyebrow: "Human-confirmed mapping",
    title: "Make different labels mean the same thing",
    description: "The tool suggests a shared field for each column. Nothing is used until a person confirms the match.",
    icon: Columns3,
    scene: "mapping",
  },
  {
    id: "review-duplicates",
    label: "Review duplicates",
    eyebrow: "Explainable matching",
    title: "See why two records look alike",
    description: "Compare names, dates, programs, and amounts side by side, then decide whether to link or keep them separate.",
    icon: ScanSearch,
    scene: "duplicates",
  },
  {
    id: "define-metrics",
    label: "Define metrics",
    eyebrow: "Auditable calculation",
    title: "Approve the meaning before the number",
    description: "Describe the metric in plain language, inspect the exact formula, and save it only after confirmation.",
    icon: Sigma,
    scene: "metrics",
  },
  {
    id: "share-report",
    label: "Share the report",
    eyebrow: "Source-linked reporting",
    title: "Follow every result back to evidence",
    description: "Share a protected report where every number opens its source records and every unresolved gap remains visible.",
    icon: Fingerprint,
    scene: "report",
  },
] as const

export function HowItWorks() {
  const [activeIndex, setActiveIndex] = useState(0)
  const activeStep = workflowSteps[activeIndex]
  const ActiveIcon = activeStep.icon

  function selectStep(index: number) {
    setActiveIndex(index)
  }

  function moveSelection(event: KeyboardEvent<HTMLDivElement>) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const lastIndex = workflowSteps.length - 1
    const nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? lastIndex : event.key === 'ArrowRight' ? (activeIndex + 1) % workflowSteps.length : (activeIndex - 1 + workflowSteps.length) % workflowSteps.length
    setActiveIndex(nextIndex)
    document.getElementById(`workflow-tab-${nextIndex}`)?.focus()
  }

  return <section className="how-it-works" id="how-it-works"><p className="eyebrow">A transparent path from file to finding</p><div className="workflow-heading"><h2>How it works</h2><p>Choose a step to see how your evidence moves forward without losing its history.</p></div><div className="process-rail" role="tablist" aria-label="Reporting workflow" onKeyDown={moveSelection}><span className="process-track" aria-hidden="true"><span style={{ width: `${activeIndex * 25}%` }} /></span>{workflowSteps.map((step, index) => <button id={`workflow-tab-${index}`} key={step.id} type="button" role="tab" aria-selected={activeIndex === index} aria-controls="workflow-panel" tabIndex={activeIndex === index ? 0 : -1} data-active={activeIndex === index} data-complete={index < activeIndex} onPointerDown={() => selectStep(index)} onClick={() => selectStep(index)}><span className="step-number">{index < activeIndex ? <Check size={17} strokeWidth={2.4} /> : index + 1}</span><strong>{step.label}</strong></button>)}</div><article id="workflow-panel" className="workflow-panel" role="tabpanel" aria-labelledby={`workflow-tab-${activeIndex}`} key={activeStep.id}><div className="workflow-copy"><span className="workflow-kicker"><ActiveIcon size={17} />{activeStep.eyebrow}</span><h3>{activeStep.title}</h3><p>{activeStep.description}</p><span className="workflow-status"><Check size={15} />Your confirmation is required</span></div><WorkflowScene scene={activeStep.scene} /></article></section>
}

function WorkflowScene({ scene }: { scene: typeof workflowSteps[number]["scene"] }) {
  if (scene === "files") return <div className="workflow-scene file-scene" aria-label="Two source files being stored"><div className="scene-file"><FileCheck2 /><span><strong>attendance_q3.csv</strong><small>276 original rows</small></span><b>Stored</b></div><div className="scene-file"><FileCheck2 /><span><strong>survey_results.xlsx</strong><small>64 original rows</small></span><b>Stored</b></div><div className="scene-rule"><Fingerprint size={16} />Original rows remain unchanged</div></div>

  if (scene === "mapping") return <div className="workflow-scene mapping-scene" aria-label="Columns being mapped"><div className="scene-map-row"><span>Participant Name</span><i>→</i><strong>beneficiary_name</strong><b>94%</b></div><div className="scene-map-row"><span>Session date</span><i>→</i><strong>event_date</strong><b>88%</b></div><div className="scene-map-row pending"><span>Area</span><i>→</i><strong>Choose a field</strong><b>Check</b></div></div>

  if (scene === "duplicates") return <div className="workflow-scene duplicate-scene" aria-label="Two possible duplicate records compared"><div className="mini-record"><small>attendance_q3.csv</small><strong>B-4f21</strong><span>Nutrition · 12 Sep</span></div><div className="match-score"><strong>92%</strong><span>possible match</span></div><div className="mini-record"><small>workshops_q3.csv</small><strong>B-91ac</strong><span>Nutrition · 12 Sep</span></div><div className="similarity-bars"><span><small>Name</small><i><b style={{ width: "96%" }} /></i></span><span><small>Date</small><i><b style={{ width: "100%" }} /></i></span><span><small>Program</small><i><b style={{ width: "84%" }} /></i></span></div></div>

  if (scene === "metrics") return <div className="workflow-scene metric-scene" aria-label="A metric formula being reviewed"><small>Plain-language request</small><p>Unique beneficiaries served in the nutrition program</p><div className="formula-preview"><span>Count distinct</span><strong>beneficiary_id</strong><i>where</i><span>program = Nutrition</span></div><div className="scene-confirm"><Check size={16} />Formula ready for your review</div></div>

  return <div className="workflow-scene report-scene" aria-label="A source-linked report result"><div className="mini-result"><span>Beneficiaries served</span><strong>184</strong><small>Click to view 184 source records</small></div><div className="mini-lineage"><span>2 files</span><i /><span>8 mappings</span><i /><span>184 records</span></div><div className="mini-gap"><b>Data gap</b><span>3 source rows are missing dates</span></div></div>
}
