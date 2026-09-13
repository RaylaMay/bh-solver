import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Flame,
  GitMerge,
  GitPullRequest,
  Orbit,
  Repeat2,
  type LucideIcon,
} from 'lucide-react'
import type { EquipmentKind, ParameterValue } from './types'

export interface EquipmentDefinition {
  kind: EquipmentKind
  label: string
  group: 'Boundary' | 'Transfer' | 'Network'
  icon: LucideIcon
  inputs: number
  outputs: number
  parameters: Record<string, ParameterValue>
}

const quantity = (label: string, value: number, unit: string): ParameterValue => ({
  label,
  quantity: { value, unit },
})

export const equipmentCatalog: EquipmentDefinition[] = [
  { kind: 'source', label: 'Source', group: 'Boundary', icon: ArrowUpFromLine, inputs: 0, outputs: 1, parameters: { temperature: quantity('Temperature', 300, 'K'), pressure: quantity('Pressure', 101325, 'Pa'), massFlow: quantity('Mass flow', 1, 'kg/s') } },
  { kind: 'sink', label: 'Sink', group: 'Boundary', icon: ArrowDownToLine, inputs: 1, outputs: 0, parameters: {} },
  { kind: 'heater', label: 'Heater / cooler', group: 'Transfer', icon: Flame, inputs: 1, outputs: 1, parameters: { duty: quantity('Specified duty', 500000, 'W') } },
  { kind: 'heat-exchanger', label: 'Heat exchanger', group: 'Transfer', icon: Repeat2, inputs: 2, outputs: 2, parameters: { effectiveness: quantity('Effectiveness', 0.8, '1') } },
  { kind: 'radiator', label: 'Radiator', group: 'Transfer', icon: Orbit, inputs: 1, outputs: 1, parameters: { targetTemperature: quantity('Target outlet temperature', 500, 'K'), emissivity: quantity('Effective emissivity', 0.9, '1') } },
  { kind: 'mixer', label: 'Mixer', group: 'Network', icon: GitMerge, inputs: 2, outputs: 1, parameters: {} },
  { kind: 'splitter', label: 'Splitter', group: 'Network', icon: GitPullRequest, inputs: 1, outputs: 2, parameters: { splitFraction: quantity('Outlet A fraction', 0.5, '1') } },
]

export const getEquipment = (kind: EquipmentKind) => {
  const definition = equipmentCatalog.find((item) => item.kind === kind)
  if (!definition) throw new Error(`Unknown equipment kind: ${kind}`)
  return definition
}
