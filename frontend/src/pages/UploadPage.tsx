import { ArrowRight, Check, FileSpreadsheet, LoaderCircle, Pencil, ShieldCheck, Trash2, UploadCloud, X } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"

import { AppShell } from "../components/AppShell"
import { Button, Chip, EmptyState } from "../components/ui"
import { archiveUpload, getUploads, renameUpload, suggestMappings, uploadFile } from "../lib/api"
import { useFlow } from "../state/useFlow"
import type { Upload } from "../types"

export function UploadPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const { updateFlow } = useFlow()
  const [uploads, setUploads] = useState<Upload[]>([])
  const [queue, setQueue] = useState<File[]>([])
  const [busy, setBusy] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState((location.state as { notice?: string } | null)?.notice || "")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [confirmingId, setConfirmingId] = useState<string | null>(null)
  const [actionId, setActionId] = useState<string | null>(null)
  const [draftName, setDraftName] = useState("")

  useEffect(() => {
    getUploads().then(setUploads).catch(() => setError("Existing uploads could not be loaded."))
  }, [])

  const addFiles = useCallback((files: FileList | File[]) => {
    const accepted = Array.from(files).filter((file) => /\.(csv|xlsx|xls|json)$/i.test(file.name))
    setQueue((current) => [...current, ...accepted])
    if (accepted.length !== files.length) setError("Only CSV, XLSX, XLS, and JSON files are accepted.")
  }, [])

  async function storeFiles() {
    if (!queue.length) return
    setBusy(true)
    setError("")
    try {
      const newIds: string[] = []
      for (const file of queue) {
        const job = await uploadFile(file)
        const uploadId = job.result?.upload_id
        if (!uploadId) throw new Error("The upload completed without a source ID")
        newIds.push(uploadId)
        await suggestMappings(uploadId)
      }
      const latest = await getUploads()
      setUploads(latest)
      setQueue([])
      updateFlow({ uploadIds: latest.map((upload) => upload.id), mappingsConfirmed: false, reviewStarted: false, metricCreated: false })
      setNotice(`${newIds.length} file${newIds.length === 1 ? "" : "s"} stored without changing the originals.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The files could not be processed. Check their format and try again.")
    } finally {
      setBusy(false)
    }
  }

  function beginEditing(upload: Upload) {
    setEditingId(upload.id)
    setConfirmingId(null)
    setDraftName(upload.filename)
    setError("")
  }

  function cancelEditing() {
    setEditingId(null)
    setDraftName("")
  }

  async function saveLabel(upload: Upload) {
    const displayName = draftName.trim()
    if (!displayName) {
      setError("The display name cannot be empty.")
      return
    }
    setActionId(upload.id)
    setError("")
    try {
      await renameUpload(upload.id, displayName)
      const latest = await getUploads()
      setUploads(latest)
      setEditingId(null)
      setDraftName("")
      setNotice(`Display label updated. The original source file remains ${upload.original_filename || upload.filename}.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The display label could not be updated.")
    } finally {
      setActionId(null)
    }
  }

  async function removeStoredFile(upload: Upload) {
    setActionId(upload.id)
    setError("")
    try {
      const result = await archiveUpload(upload.id)
      const latest = await getUploads()
      setUploads(latest)
      setConfirmingId(null)
      updateFlow({ uploadIds: latest.map((item) => item.id), mappingsConfirmed: false, reviewStarted: false, metricCreated: false })
      setNotice(`${upload.filename} was removed from this report. ${result.raw_records_retained} raw record${result.raw_records_retained === 1 ? " remains" : "s remain"} preserved in the audit layer.`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The file could not be removed from this report.")
    } finally {
      setActionId(null)
    }
  }

  return <AppShell><main className="page page-fade"><header className="page-heading"><p className="eyebrow">Step 1 of 5</p><h1>Add your files</h1><p>Bring together the small spreadsheets and exports behind your program report.</p></header>{notice && <button className="notice" onClick={() => setNotice("")}>{notice}<span>Dismiss</span></button>}{error && <p className="inline-error" role="alert">{error}</p>}<section className="dropzone" data-dragging={dragging} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); addFiles(event.dataTransfer.files) }}><span className="dropzone-icon"><UploadCloud size={28} aria-hidden="true" /></span><h2>Drop CSV or Excel files here</h2><p>or choose files from your computer</p><Button onClick={() => inputRef.current?.click()}>Browse files</Button><input ref={inputRef} className="visually-hidden" type="file" multiple accept=".csv,.xlsx,.xls,.json" onChange={(event) => event.target.files && addFiles(event.target.files)} /><small>CSV, XLSX, XLS or JSON · uploads process in the background</small></section>{queue.length > 0 && <section className="file-queue" aria-label="Files ready to upload"><div className="section-title"><h2>Ready to store</h2><span>{queue.length} selected</span></div>{queue.map((file, index) => <div className="file-row" key={`${file.name}-${file.lastModified}`}><FileSpreadsheet aria-hidden="true" /><div><strong>{file.name}</strong><span>{formatBytes(file.size)}</span></div><button onClick={() => setQueue((current) => current.filter((_, itemIndex) => itemIndex !== index))} aria-label={`Remove ${file.name}`}><X size={17} /></button></div>)}<Button variant="primary" disabled={busy} onClick={storeFiles}>{busy ? <LoaderCircle className="spin" size={17} /> : <ShieldCheck size={17} />}{busy ? "Storing originals…" : "Store selected files"}</Button></section>}<section className="stored-files"><div className="section-title"><div><p className="eyebrow">Immutable source layer</p><h2>Stored files</h2></div><span>{uploads.length} active</span></div>{uploads.length ? uploads.map((upload) => <StoredFile key={upload.id} upload={upload} editing={editingId === upload.id} confirming={confirmingId === upload.id} busy={actionId === upload.id} draftName={draftName} setDraftName={setDraftName} beginEditing={() => beginEditing(upload)} cancelEditing={cancelEditing} saveLabel={() => saveLabel(upload)} requestRemoval={() => { setConfirmingId(upload.id); setEditingId(null) }} cancelRemoval={() => setConfirmingId(null)} confirmRemoval={() => removeStoredFile(upload)} />) : <EmptyState title="No active files" text="Add a source file above. Removed files remain preserved in the audit layer." />}</section><aside className="immutable-note"><ShieldCheck aria-hidden="true" /><div><strong>We keep your originals exactly as they are.</strong><p>Display-name changes and removals are saved as separate audit entries. Raw rows are never overwritten or physically deleted.</p></div></aside><footer className="page-actions"><Button variant="primary" disabled={!uploads.length || busy} onClick={() => navigate("/match")}>Continue to mapping <ArrowRight size={17} /></Button></footer></main></AppShell>
}

type StoredFileProps = {
  upload: Upload
  editing: boolean
  confirming: boolean
  busy: boolean
  draftName: string
  setDraftName: (value: string) => void
  beginEditing: () => void
  cancelEditing: () => void
  saveLabel: () => void
  requestRemoval: () => void
  cancelRemoval: () => void
  confirmRemoval: () => void
}

function StoredFile({ upload, editing, confirming, busy, draftName, setDraftName, beginEditing, cancelEditing, saveLabel, requestRemoval, cancelRemoval, confirmRemoval }: StoredFileProps) {
  const originalName = upload.original_filename || upload.filename
  const renamed = originalName !== upload.filename

  return <article className="stored-file"><div className="stored-file-row"><FileSpreadsheet aria-hidden="true" /><div className="stored-file-details">{editing ? <label className="stored-file-editor"><span className="visually-hidden">Display name for {originalName}</span><input value={draftName} onChange={(event) => setDraftName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") saveLabel(); if (event.key === "Escape") cancelEditing() }} autoFocus /></label> : <strong>{upload.filename}</strong>}<span>{upload.row_count ?? "Raw"} {upload.row_count === 1 ? "row" : "rows"} · {upload.columns.length} columns · {new Date(upload.created_at).toLocaleDateString()}</span>{renamed && <small>Original source: {originalName}</small>}</div><div className="stored-file-actions"><Chip tone="good">Stored</Chip>{editing ? <><button className="file-action save" type="button" onClick={saveLabel} disabled={busy} aria-label={`Save display name for ${originalName}`}>{busy ? <LoaderCircle className="spin" size={16} /> : <Check size={16} />}<span>Save</span></button><button className="file-action" type="button" onClick={cancelEditing} disabled={busy}><X size={16} /><span>Cancel</span></button></> : <><button className="file-action" type="button" onClick={beginEditing}><Pencil size={15} /><span>Edit</span></button><button className="file-action danger" type="button" onClick={requestRemoval}><Trash2 size={15} /><span>Remove</span></button></>}</div></div>{confirming && <div className="remove-confirmation" role="alertdialog" aria-labelledby={`remove-title-${upload.id}`}><div><strong id={`remove-title-${upload.id}`}>Remove {upload.filename} from this report?</strong><span>The original file and its {upload.row_count ?? 0} raw records will remain preserved in the audit layer.</span></div><Button onClick={cancelRemoval} disabled={busy}>Keep file</Button><Button className="danger-button" onClick={confirmRemoval} disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <Trash2 size={16} />}{busy ? "Removing…" : "Remove from report"}</Button></div>}</article>
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}
