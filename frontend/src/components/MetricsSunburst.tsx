import { useMemo } from "react"

import type { Metric, SourceRecord } from "../types"

type MetricsSunburstProps = {
  metrics: Metric[]
  records: SourceRecord[]
  selectedIndex: number
  onSelect: (index: number) => void
}

type Segment = {
  metric: Metric
  metricIndex: number
  startAngle: number
  endAngle: number
  sources: Array<{ name: string; count: number; startAngle: number; endAngle: number }>
}

const center = 160
const fullCircle = Math.PI * 2

export function MetricsSunburst({ metrics, records, selectedIndex, onSelect }: MetricsSunburstProps) {
  const segments = useMemo(() => buildSegments(metrics, records), [metrics, records])
  const selectedMetric = metrics[selectedIndex]

  return <section className="metric-landscape" aria-labelledby="metric-landscape-title">
    <header className="metric-landscape-header">
      <div>
        <p className="eyebrow">Metric landscape</p>
        <h2 id="metric-landscape-title">How the evidence is distributed</h2>
      </div>
      <p>Inner segments are metrics. Outer segments show their source files. Segment width reflects source-linked records.</p>
    </header>
    <div className="sunburst-layout">
      <div className="sunburst-chart">
        <svg viewBox="0 0 320 320" role="img" aria-label="Interactive sunburst of metrics and their source files">
          <circle className="sunburst-guide" cx={center} cy={center} r="151" />
          {segments.map((segment) => <g key={segment.metric.id} className="sunburst-group" data-selected={segment.metricIndex === selectedIndex}>
            <path
              className={`sunburst-segment sunburst-tone-${segment.metricIndex % 4}`}
              d={arcPath(61, 105, segment.startAngle, segment.endAngle)}
              data-ring="metric"
              role="button"
              tabIndex={0}
              aria-label={`${segment.metric.name}, ${formatValue(segment.metric.value)}, ${segment.metric.source_record_ids.length} source-linked records`}
              onClick={() => onSelect(segment.metricIndex)}
              onKeyDown={(event) => handleKeySelect(event, () => onSelect(segment.metricIndex))}
            >
              <title>{segment.metric.name}: {formatValue(segment.metric.value)}</title>
            </path>
            {segment.sources.map((source) => <path
              key={`${segment.metric.id}-${source.name}`}
              className={`sunburst-segment sunburst-tone-${segment.metricIndex % 4}`}
              d={arcPath(110, 148, source.startAngle, source.endAngle)}
              data-ring="source"
              role="button"
              tabIndex={0}
              aria-label={`${source.name}, ${source.count} records supporting ${segment.metric.name}`}
              onClick={() => onSelect(segment.metricIndex)}
              onKeyDown={(event) => handleKeySelect(event, () => onSelect(segment.metricIndex))}
            >
              <title>{source.name}: {source.count} records</title>
            </path>)}
          </g>)}
          <circle className="sunburst-center" cx={center} cy={center} r="53" />
          <text className="sunburst-center-value" x={center} y="153" textAnchor="middle">{formatValue(selectedMetric.value)}</text>
          <text className="sunburst-center-label" x={center} y="176" textAnchor="middle">{operationLabel(selectedMetric)}</text>
        </svg>
      </div>
      <div className="sunburst-legend" aria-label="Select a metric">
        {metrics.map((metric, index) => <button key={metric.id} type="button" data-selected={index === selectedIndex} onClick={() => onSelect(index)}>
          <span className={`sunburst-swatch sunburst-tone-${index % 4}`} aria-hidden="true" />
          <span className="sunburst-legend-copy">
            <strong>{metric.name}</strong>
            <small>{operationLabel(metric)} · {metric.source_record_ids.length} source-linked records</small>
          </span>
          <b>{formatValue(metric.value)}</b>
        </button>)}
      </div>
    </div>
  </section>
}

function buildSegments(metrics: Metric[], records: SourceRecord[]) {
  const sourceByRecord = new Map(records.map((record) => [record.source_record_id, record.source.split(" · ")[0]]))
  const weights = metrics.map((metric) => Math.max(metric.source_record_ids.length, 1))
  const totalWeight = weights.reduce((sum, weight) => sum + weight, 0)
  const metricGap = metrics.length > 1 ? 0.025 : 0.012
  let cursor = -Math.PI / 2

  return metrics.map((metric, metricIndex): Segment => {
    const angle = fullCircle * (weights[metricIndex] / totalWeight)
    const startAngle = cursor + metricGap
    const endAngle = cursor + angle - metricGap
    const sourceCounts = new Map<string, number>()

    metric.source_record_ids.forEach((recordId) => {
      const source = sourceByRecord.get(recordId) || "Unresolved source"
      sourceCounts.set(source, (sourceCounts.get(source) || 0) + 1)
    })

    const sourceTotal = Math.max(metric.source_record_ids.length, 1)
    const availableAngle = Math.max(endAngle - startAngle, 0)
    let sourceCursor = startAngle
    const sourceGap = sourceCounts.size > 1 ? 0.014 : 0.006
    const sources = Array.from(sourceCounts, ([name, count]) => {
      const sourceAngle = availableAngle * (count / sourceTotal)
      const source = {
        name,
        count,
        startAngle: sourceCursor + sourceGap,
        endAngle: sourceCursor + sourceAngle - sourceGap,
      }
      sourceCursor += sourceAngle
      return source
    })

    cursor += angle
    return { metric, metricIndex, startAngle, endAngle, sources }
  })
}

function arcPath(innerRadius: number, outerRadius: number, startAngle: number, endAngle: number) {
  const startOuter = polarPoint(outerRadius, startAngle)
  const endOuter = polarPoint(outerRadius, endAngle)
  const startInner = polarPoint(innerRadius, startAngle)
  const endInner = polarPoint(innerRadius, endAngle)
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0
  return `M ${startOuter.x} ${startOuter.y} A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${endOuter.x} ${endOuter.y} L ${endInner.x} ${endInner.y} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${startInner.x} ${startInner.y} Z`
}

function polarPoint(radius: number, angle: number) {
  return {
    x: center + Math.cos(angle) * radius,
    y: center + Math.sin(angle) * radius,
  }
}

function handleKeySelect(event: React.KeyboardEvent<SVGPathElement>, select: () => void) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault()
    select()
  }
}

function operationLabel(metric: Metric) {
  return metric.formula.operation.replaceAll("_", " ")
}

function formatValue(value: number) {
  return new Intl.NumberFormat().format(value)
}
