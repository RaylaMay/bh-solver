import { describe, expect, it } from 'vitest'
import { getEquipment } from './catalog'
import type { EquipmentKind, PfdNode } from './types'
import { validateTopology } from './validation'

const node = (id: string, kind: EquipmentKind): PfdNode => ({ id, type: 'equipment', position: { x: 0, y: 0 }, data: { label: id, kind, status: 'draft', validity: 'UNKNOWN', parameters: structuredClone(getEquipment(kind).parameters) } })

describe('validateTopology', () => {
  it('accepts a connected source-to-sink flow', () => {
    const result = validateTopology([node('source', 'source'), node('sink', 'sink')], [{ id: 'edge', source: 'source', target: 'sink' }])
    expect(result).toEqual({ valid: true, degreesOfFreedom: 0, diagnostics: [] })
  })

  it('reports missing ports and degrees of freedom', () => {
    const result = validateTopology([node('heater', 'heater')], [])
    expect(result.valid).toBe(false)
    expect(result.degreesOfFreedom).toBe(2)
    expect(result.diagnostics.map((item) => item.code)).toEqual(['MISSING_INLET', 'MISSING_OUTLET'])
  })
})
