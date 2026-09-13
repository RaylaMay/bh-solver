import { Trash2 } from 'lucide-react'
import type { PfdNode } from '../types'

interface InspectorProps {
  node?: PfdNode
  onChange: (nodeId: string, path: string, value: string | number) => void
  onDelete: (nodeId: string) => void
}

export function Inspector({ node, onChange, onDelete }: InspectorProps) {
  if (!node) return <aside className="inspector panel empty-state"><p>Select equipment to edit its label and parameters.</p></aside>
  return (
    <aside className="inspector panel">
      <div className="panel-title"><span>Inspector</span><small>{node.id}</small></div>
      <label className="field"><span>Name</span><input value={node.data.label} onChange={(event) => onChange(node.id, 'label', event.target.value)} /></label>
      <div className="section-label">Parameters</div>
      {Object.entries(node.data.parameters).length === 0 && <p className="muted">No user parameters for this model.</p>}
      {Object.entries(node.data.parameters).map(([key, parameter]) => (
        <label className="field" key={key}>
          <span>{parameter.label}</span>
          <div className="quantity-input"><input type="number" value={parameter.quantity.value} onChange={(event) => onChange(node.id, `parameters.${key}.quantity.value`, Number(event.target.value))} /><input className="unit" value={parameter.quantity.unit} onChange={(event) => onChange(node.id, `parameters.${key}.quantity.unit`, event.target.value)} aria-label={`${parameter.label} unit`} /></div>
        </label>
      ))}
      <button className="danger ghost inspector-delete" onClick={() => onDelete(node.id)}><Trash2 size={15} /> Delete equipment</button>
    </aside>
  )
}
