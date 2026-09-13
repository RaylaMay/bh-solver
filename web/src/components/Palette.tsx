import { equipmentCatalog } from '../catalog'
import type { EquipmentKind } from '../types'

export function Palette({ onAdd }: { onAdd: (kind: EquipmentKind) => void }) {
  return (
    <aside className="palette panel">
      <div className="panel-title"><span>Equipment</span><small>Click to add</small></div>
      {(['Boundary', 'Transfer', 'Network'] as const).map((group) => (
        <section key={group}>
          <h3>{group}</h3>
          <div className="palette-grid">
            {equipmentCatalog.filter((item) => item.group === group).map((item) => {
              const Icon = item.icon
              return <button key={item.kind} onClick={() => onAdd(item.kind)} title={`Add ${item.label}`}><Icon size={17} /><span>{item.label}</span></button>
            })}
          </div>
        </section>
      ))}
    </aside>
  )
}
