import { AlertCircle, CheckCircle2, CircleDotDashed } from 'lucide-react'
import type { Diagnostic, RunResult, ValidationResult } from '../types'

export function ResultsPanel({ validation, run, previousRun, busy, serviceError }: { validation?: ValidationResult; run?: RunResult; previousRun?: RunResult; busy?: string; serviceError?: string }) {
  const diagnostics: Diagnostic[] = serviceError
    ? [{ severity: 'error', code: 'SERVICE_UNAVAILABLE', message: serviceError }]
    : (run?.diagnostics ?? validation?.diagnostics ?? [])
  const success = run?.converged ?? validation?.valid
  const comparison = run && previousRun ? run.nodeResults.flatMap((node) => {
    const prior = previousRun.nodeResults.find((item) => item.nodeId === node.nodeId)
    return node.metrics.flatMap((metric) => {
      const priorMetric = prior?.metrics.find((item) => item.label === metric.label)
      return priorMetric && priorMetric.displayValue !== metric.displayValue
        ? [{ nodeId: node.nodeId, label: metric.label, prior: priorMetric.displayValue, current: metric.displayValue }]
        : []
    })
  }) : []
  return (
    <section className="results panel">
      <div className="panel-title"><span>Validation & results</span>{busy && <small className="working"><CircleDotDashed size={13} /> {busy}</small>}</div>
      {!validation && !run && !serviceError && <div className="result-placeholder"><CircleDotDashed size={22} /><span>Validate the draft to inspect readiness.</span></div>}
      {(validation || run) && <div className={`result-summary ${success ? 'success' : 'error'}`}>
        {success ? <CheckCircle2 size={19} /> : <AlertCircle size={19} />}
        <div><strong>{run ? (run.converged ? 'Run converged' : 'Run failed') : (validation?.valid ? 'Draft is valid' : 'Draft needs attention')}</strong><small>{run ? `Run ${run.runId}` : `${validation?.degreesOfFreedom ?? 0} degree(s) of freedom`}</small></div>
      </div>}
      <div className="diagnostic-list">
        {diagnostics.map((item, index) => <div className={`diagnostic ${item.severity}`} key={`${item.code}-${index}`}><b>{item.code}</b><span>{item.message}</span></div>)}
      </div>
      {run && previousRun && <div className="diagnostic-list"><div className="diagnostic info"><b>REVISION_COMPARE</b><span>{comparison.length === 0 ? 'No displayed metrics changed' : `${comparison.length} displayed metric(s) changed`} from prior run {previousRun.runId}.</span></div>{comparison.slice(0, 8).map((item) => <div className="diagnostic info" key={`${item.nodeId}-${item.label}`}><b>{item.nodeId} · {item.label}</b><span>{item.prior} → {item.current}</span></div>)}</div>}
    </section>
  )
}
