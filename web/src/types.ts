import type { Edge, Node } from '@xyflow/react'

export const API_VERSION = 'v1alpha' as const

export type EquipmentKind =
  | 'source'
  | 'sink'
  | 'heater'
  | 'mixer'
  | 'splitter'
  | 'heat-exchanger'
  | 'radiator'

export type ModelStatus = 'draft' | 'valid' | 'warning' | 'invalid' | 'running' | 'failed'
export type ValidityClass = 'VALID' | 'EXTRAPOLATED' | 'INVALID' | 'UNKNOWN'

export interface Quantity {
  value: number
  unit: string
}

export interface ParameterValue {
  label: string
  quantity: Quantity
  description?: string
}

export interface MetricValue {
  label: string
  displayValue: string
}

export interface PfdNodeData extends Record<string, unknown> {
  label: string
  kind: EquipmentKind
  status: ModelStatus
  validity: ValidityClass
  parameters: Record<string, ParameterValue>
  metrics?: MetricValue[]
}

export type PfdNode = Node<PfdNodeData, 'equipment'>
export type PfdEdge = Edge

export interface DraftRevision {
  schemaVersion: typeof API_VERSION
  draftId: string
  revision: number
  baseCaseId: string | null
  updatedAt: string
  nodes: PfdNode[]
  edges: PfdEdge[]
}

export interface Diagnostic {
  severity: 'info' | 'warning' | 'error'
  code: string
  message: string
  subjectId?: string
}

export interface ValidationResult {
  valid: boolean
  degreesOfFreedom: number
  diagnostics: Diagnostic[]
}

export interface NodeResult {
  nodeId: string
  status: ModelStatus
  validity: ValidityClass
  metrics: MetricValue[]
}

export interface RunResult {
  runId: string
  draftId: string
  revision: number
  converged: boolean
  conservationClosed: boolean
  diagnostics: Diagnostic[]
  nodeResults: NodeResult[]
  completedAt: string
}

export interface ApiEnvelope<T> {
  apiVersion: typeof API_VERSION
  data: T
}
