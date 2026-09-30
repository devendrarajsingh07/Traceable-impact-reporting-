import axios from "axios"

import type { Duplicate, Job, Lineage, Mapping, MetricSuggestion, Report, Upload } from "../types"

export const api = axios.create({ baseURL: "/api", timeout: 15000 })

export async function getUploads() {
  return (await api.get<Upload[]>("/uploads")).data
}

export async function renameUpload(uploadId: string, displayName: string) {
  return (await api.patch<Upload>(`/uploads/${uploadId}`, { display_name: displayName, actor: "ui-reviewer" })).data
}

export async function archiveUpload(uploadId: string) {
  return (await api.delete<{ id: string; status: string; raw_records_retained: number }>(`/uploads/${uploadId}`)).data
}

export async function waitForJob(jobId: string) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const job = (await api.get<Job>(`/jobs/${jobId}`)).data
    if (job.status === "completed") return job
    if (job.status === "failed") throw new Error(job.error || "Background job failed")
    await new Promise((resolve) => window.setTimeout(resolve, 500))
  }
  throw new Error("Background job timed out")
}

export async function uploadFile(file: File) {
  const form = new FormData()
  form.append("file", file)
  const accepted = (await api.post<{ job_id: string }>("/uploads", form)).data
  return waitForJob(accepted.job_id)
}

export async function suggestMappings(uploadId: string) {
  return (await api.post<Mapping[]>(`/uploads/${uploadId}/mapping-suggestions`)).data
}

export async function getMappings() {
  return (await api.get<Mapping[]>("/mappings")).data
}

export async function confirmMapping(mappingId: string, canonicalField: string) {
  return (await api.post(`/mappings/${mappingId}/confirm`, { canonical_field: canonicalField, actor: "ui-reviewer" })).data
}

export async function scanDuplicates() {
  const accepted = (await api.post<{ job_id: string }>("/duplicates/scan")).data
  return waitForJob(accepted.job_id)
}

export async function getDuplicates() {
  return (await api.get<Duplicate[]>("/duplicates")).data
}

export async function decideDuplicate(candidateId: string, decision: string) {
  return (await api.post(`/duplicates/${candidateId}/decision`, { decision, actor: "ui-reviewer" })).data
}

export async function suggestMetric(description: string) {
  return (await api.post<MetricSuggestion>("/report/metric-definition/suggest", { description })).data
}

export async function createMetric(payload: Record<string, unknown>) {
  return (await api.post("/report/metric-definition", payload)).data
}

export async function computeMetric(metricId: string) {
  return (await api.post(`/metrics/${metricId}/compute`)).data
}

export async function getReport() {
  return (await api.get<Report>("/report")).data
}

export async function getLineage() {
  return (await api.get<Lineage>("/lineage")).data
}

export async function login(username: string, password: string) {
  return (await api.post<{ access_token: string; role: string }>("/auth/token", { username, password })).data
}

export async function createShareLink(accessToken: string) {
  return (await api.post<{ token: string; url: string }>("/share-links", {}, { headers: { Authorization: `Bearer ${accessToken}` } })).data
}

export async function getSharedReport(token: string) {
  return (await api.get<Report>(`/public/reports/${token}`)).data
}
