export type Stage = "upload" | "mapping" | "review" | "metrics" | "lineage" | "report"

export type Job = {
  id: string
  status: "queued" | "running" | "completed" | "failed"
  progress: number
  result?: { upload_id?: string; created?: number }
  error?: string
}

export type Upload = {
  id: string
  filename: string
  original_filename?: string
  sha256: string
  columns: string[]
  row_count?: number
  created_at: string
}

export type Mapping = {
  id: string
  upload_id: string
  raw_column: string
  canonical_field: string
  confidence: number
  status: string
}

export type Duplicate = {
  id: string
  left_record_id: string
  right_record_id: string
  score: number
  reasons: {
    algorithm?: string
    threshold?: number
    field_similarities?: Record<string, number>
  }
  status: string
  model_version: string
}

export type Filter = {
  field: string
  operator: "eq" | "neq" | "not_empty" | "gte" | "lte" | "contains"
  value?: unknown
}

export type Formula = {
  operation: "count" | "count_distinct" | "sum" | "avg" | "average" | "min" | "max"
  field?: string
  filters: Filter[]
}

export type MetricSuggestion = {
  suggestion_id: string
  formula_spec: Formula | null
  restatement: string
  clarification_needed: string | null
  canonical_schema: string[]
}

export type Metric = {
  id: string
  name: string
  description: string
  formula: Formula
  value: number
  source_record_ids: string[]
  caveats: string[]
  origin?: string
}

export type SourceRecord = {
  source_record_id: string
  pseudonym: string
  source: string
  values: Record<string, unknown>
}

export type DataGap = {
  type: string
  label: string
  count: number
  severity: "warning" | "info"
}

export type LineageNode = {
  id: string
  label: string
  type: "upload" | "mapping" | "record_set" | "metric"
  source_record_ids?: string[]
}

export type LineageEdge = {
  source: string
  target: string
  record_count?: number
}

export type Lineage = {
  nodes: LineageNode[]
  edges: LineageEdge[]
}

export type Report = {
  title: string
  generated_at: string
  metrics: Metric[]
  contributing_records: SourceRecord[]
  data_gaps: DataGap[]
  audit_trail: Array<{
    id: string
    action: string
    entity_type: string
    entity_id: string
    actor: string
    details: Record<string, unknown>
    created_at: string
  }>
  lineage?: Lineage
  privacy_note: string
}
