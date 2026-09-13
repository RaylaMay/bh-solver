import { Handle, Position, type NodeProps } from '@xyflow/react'
import { AlertTriangle, CheckCircle2, LoaderCircle } from 'lucide-react'
import { getEquipment } from '../catalog'
import type { PfdNode } from '../types'

const statusIcon = {
  valid: <CheckCircle2 size={14} aria-label="Valid" />,
  warning: <AlertTriangle size={14} aria-label="Warning" />,
  invalid: <AlertTriangle size={14} aria-label="Invalid" />,
  failed: <AlertTriangle size={14} aria-label="Failed" />,
  running: <LoaderCircle size={14} className="spin" aria-label="Running" />,
  draft: null,
}

export function EquipmentNode({ data, selected }: NodeProps<PfdNode>) {
  const definition = getEquipment(data.kind)
  const Icon = definition.icon
  const inputs = Array.from({ length: definition.inputs })
  const outputs = Array.from({ length: definition.outputs })

  return (
    <div className={`equipment-node status-${data.status} ${selected ? 'selected' : ''}`}>
      {inputs.map((_, index) => (
        <Handle key={`in-${index}`} id={`in-${index}`} type="target" position={Position.Left} style={{ top: `${((index + 1) / (inputs.length + 1)) * 100}%` }} />
      ))}
      <div className="equipment-node__header">
        <span className="equipment-node__icon"><Icon size={18} /></span>
        <span className="equipment-node__status">{statusIcon[data.status]}</span>
      </div>
      <strong>{data.label}</strong>
      <small>{definition.label}</small>
      {data.metrics?.slice(0, 2).map((metric) => (
        <div className="node-metric" key={metric.label}><span>{metric.label}</span><b>{metric.displayValue}</b></div>
      ))}
      {data.validity === 'EXTRAPOLATED' && <span className="validity-chip">Extrapolated</span>}
      {outputs.map((_, index) => (
        <Handle key={`out-${index}`} id={`out-${index}`} type="source" position={Position.Right} style={{ top: `${((index + 1) / (outputs.length + 1)) * 100}%` }} />
      ))}
    </div>
  )
}
