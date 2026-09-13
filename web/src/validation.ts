import { getEquipment } from './catalog'
import type { Diagnostic, PfdEdge, PfdNode, ValidationResult } from './types'

export function validateTopology(nodes: PfdNode[], edges: PfdEdge[]): ValidationResult {
  const diagnostics: Diagnostic[] = []
  let degreesOfFreedom = 0

  if (nodes.length === 0) {
    diagnostics.push({ severity: 'error', code: 'EMPTY_FLOWSHEET', message: 'Add equipment to begin a flowsheet.' })
  }

  for (const node of nodes) {
    const definition = getEquipment(node.data.kind)
    const incoming = edges.filter((edge) => edge.target === node.id).length
    const outgoing = edges.filter((edge) => edge.source === node.id).length
    if (incoming < definition.inputs) {
      const missing = definition.inputs - incoming
      degreesOfFreedom += missing
      diagnostics.push({ severity: 'error', code: 'MISSING_INLET', subjectId: node.id, message: `${node.data.label} has ${missing} unconnected inlet${missing === 1 ? '' : 's'}.` })
    }
    if (outgoing < definition.outputs) {
      const missing = definition.outputs - outgoing
      degreesOfFreedom += missing
      diagnostics.push({ severity: 'error', code: 'MISSING_OUTLET', subjectId: node.id, message: `${node.data.label} has ${missing} unconnected outlet${missing === 1 ? '' : 's'}.` })
    }
  }

  return { valid: diagnostics.every((item) => item.severity !== 'error'), degreesOfFreedom, diagnostics }
}
