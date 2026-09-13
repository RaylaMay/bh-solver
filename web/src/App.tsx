import { useCallback, useMemo, useState } from 'react'
import {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  type Connection,
  type NodeTypes,
} from '@xyflow/react'
import { CheckCircle2, CloudOff, FolderOpen, Play, Save, ShieldCheck } from 'lucide-react'
import '@xyflow/react/dist/style.css'
import './styles.css'
import { V1AlphaClient } from './api/client'
import { getEquipment } from './catalog'
import { EquipmentNode } from './components/EquipmentNode'
import { Inspector } from './components/Inspector'
import { Palette } from './components/Palette'
import { ResultsPanel } from './components/ResultsPanel'
import { validateTopology } from './validation'
import { API_VERSION, type DraftRevision, type EquipmentKind, type PfdEdge, type PfdNode, type RunResult, type ValidationResult } from './types'

const nodeTypes: NodeTypes = { equipment: EquipmentNode }
const api = new V1AlphaClient()

const initialNodes: PfdNode[] = [
  { id: 'source-1', type: 'equipment', position: { x: 90, y: 180 }, data: { label: 'Primary loop feed', kind: 'source', status: 'draft', validity: 'UNKNOWN', parameters: structuredClone(getEquipment('source').parameters) } },
  { id: 'heater-1', type: 'equipment', position: { x: 340, y: 180 }, data: { label: 'Reactor heat load', kind: 'heater', status: 'draft', validity: 'UNKNOWN', parameters: structuredClone(getEquipment('heater').parameters) } },
  { id: 'radiator-1', type: 'equipment', position: { x: 600, y: 180 }, data: { label: 'Main radiator', kind: 'radiator', status: 'draft', validity: 'UNKNOWN', parameters: structuredClone(getEquipment('radiator').parameters) } },
  { id: 'sink-1', type: 'equipment', position: { x: 850, y: 180 }, data: { label: 'Return boundary', kind: 'sink', status: 'draft', validity: 'UNKNOWN', parameters: {} } },
]

const initialEdges: PfdEdge[] = [
  { id: 'e-source-heater', source: 'source-1', sourceHandle: 'out-0', target: 'heater-1', targetHandle: 'in-0', animated: true },
  { id: 'e-heater-radiator', source: 'heater-1', sourceHandle: 'out-0', target: 'radiator-1', targetHandle: 'in-0', animated: true },
  { id: 'e-radiator-sink', source: 'radiator-1', sourceHandle: 'out-0', target: 'sink-1', targetHandle: 'in-0', animated: true },
]

function Studio() {
  const [nodes, setNodes, onNodesChange] = useNodesState<PfdNode>(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState<PfdEdge>(initialEdges)
  const [revision, setRevision] = useState(1)
  const [selectedId, setSelectedId] = useState<string>()
  const [validation, setValidation] = useState<ValidationResult>()
  const [lastRun, setLastRun] = useState<RunResult>()
  const [previousRun, setPreviousRun] = useState<RunResult>()
  const [busy, setBusy] = useState<string>()
  const [serviceError, setServiceError] = useState<string>()
  const [dirty, setDirty] = useState(false)
  const selectedNode = nodes.find((node) => node.id === selectedId)

  const draft = useMemo<DraftRevision>(() => ({ schemaVersion: API_VERSION, draftId: 'thermal-loop-concept', revision, baseCaseId: null, updatedAt: new Date().toISOString(), nodes, edges }), [edges, nodes, revision])

  const markChanged = useCallback(() => {
    setDirty(true)
    setValidation(undefined)
    setServiceError(undefined)
    setNodes((current) => current.map((node) => ({ ...node, data: { ...node.data, status: 'draft', metrics: undefined, validity: 'UNKNOWN' } })))
  }, [setNodes])

  const connect = useCallback((connection: Connection) => {
    setEdges((current) => addEdge({ ...connection, animated: true }, current))
    markChanged()
  }, [markChanged, setEdges])

  const addNode = useCallback((kind: EquipmentKind) => {
    const definition = getEquipment(kind)
    const count = nodes.filter((node) => node.data.kind === kind).length + 1
    const id = `${kind}-${crypto.randomUUID().slice(0, 8)}`
    const node: PfdNode = { id, type: 'equipment', position: { x: 260 + (count % 3) * 190, y: 90 + (count % 4) * 130 }, data: { label: `${definition.label} ${count}`, kind, status: 'draft', validity: 'UNKNOWN', parameters: structuredClone(definition.parameters) } }
    setNodes((current) => [...current, node])
    setSelectedId(id)
    markChanged()
  }, [markChanged, nodes, setNodes])

  const deleteNode = useCallback((nodeId: string) => {
    setNodes((current) => current.filter((node) => node.id !== nodeId))
    setEdges((current) => current.filter((edge) => edge.source !== nodeId && edge.target !== nodeId))
    setSelectedId(undefined)
    markChanged()
  }, [markChanged, setEdges, setNodes])

  const updateNode = useCallback((nodeId: string, path: string, value: string | number) => {
    setNodes((current) => current.map((node) => {
      if (node.id !== nodeId) return node
      if (path === 'label') return { ...node, data: { ...node.data, label: String(value) } }
      const [, key, , property] = path.split('.')
      const parameter = node.data.parameters[key]
      return { ...node, data: { ...node.data, parameters: { ...node.data.parameters, [key]: { ...parameter, quantity: { ...parameter.quantity, [property]: value } } } } }
    }))
    markChanged()
  }, [markChanged, setNodes])

  const applyValidation = useCallback((result: ValidationResult) => {
    setValidation(result)
    setNodes((current) => current.map((node) => ({ ...node, data: { ...node.data, status: result.diagnostics.some((item) => item.subjectId === node.id && item.severity === 'error') ? 'invalid' : (result.valid ? 'valid' : 'draft') } })))
  }, [setNodes])

  const validate = useCallback(async () => {
    const local = validateTopology(nodes, edges)
    applyValidation(local)
    setServiceError(undefined)
    if (!local.valid) return
    setBusy('Validating')
    try {
      applyValidation(await api.validateDraft(draft))
    } catch (error) {
      setServiceError(error instanceof Error ? `${error.message} Local topology checks passed; server validation did not run.` : 'Server validation did not run.')
    } finally { setBusy(undefined) }
  }, [applyValidation, draft, edges, nodes])

  const run = useCallback(async () => {
    const local = validateTopology(nodes, edges)
    applyValidation(local)
    if (!local.valid) return
    setBusy('Running')
    setServiceError(undefined)
    setNodes((current) => current.map((node) => ({ ...node, data: { ...node.data, status: 'running' } })))
    try {
      const result = await api.runDraft(draft)
      setRevision(result.revision)
      setDirty(false)
      if (result.converged && result.conservationClosed) {
        if (lastRun) setPreviousRun(lastRun)
        setLastRun(result)
      }
      else setServiceError(result.diagnostics.map((item) => item.message).join(' ') || 'The run failed; the last valid result has been preserved.')
      setNodes((current) => current.map((node) => {
        const nodeResult = result.nodeResults.find((item) => item.nodeId === node.id)
        return nodeResult ? { ...node, data: { ...node.data, status: nodeResult.status, validity: nodeResult.validity, metrics: nodeResult.metrics } } : node
      }))
    } catch (error) {
      setServiceError(error instanceof Error ? error.message : 'The run failed.')
      setNodes((current) => current.map((node) => ({ ...node, data: { ...node.data, status: 'failed' } })))
    } finally { setBusy(undefined) }
  }, [applyValidation, draft, edges, lastRun, nodes, setNodes])

  const save = useCallback(async () => {
    setBusy('Saving')
    setServiceError(undefined)
    try {
      const saved = await api.saveDraft(draft)
      setRevision(saved.revision)
      setDirty(false)
    } catch (error) {
      setServiceError(error instanceof Error ? error.message : 'The draft could not be saved.')
    } finally { setBusy(undefined) }
  }, [draft])

  const load = useCallback(async () => {
    setBusy('Loading')
    setServiceError(undefined)
    try {
      const loaded = await api.loadDraft(draft.draftId)
      setNodes(loaded.nodes)
      setEdges(loaded.edges)
      setRevision(loaded.revision)
      setValidation(undefined)
      setDirty(false)
      setSelectedId(undefined)
    } catch (error) {
      setServiceError(error instanceof Error ? error.message : 'The draft could not be loaded.')
    } finally { setBusy(undefined) }
  }, [draft.draftId, setEdges, setNodes])

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><div className="brand-mark">BH</div><div><strong>Process Studio</strong><span>BH engineering workspace</span></div></div>
        <div className="draft-meta"><span className="api-chip">{API_VERSION}</span><span>Thermal loop concept</span><b>Draft r{revision}{dirty ? ' •' : ''}</b></div>
        <div className="actions"><button className="ghost" onClick={load} disabled={Boolean(busy)}><FolderOpen size={16} /> Load</button><button className="ghost" onClick={save} disabled={Boolean(busy)}><Save size={16} /> Save</button><button className="secondary" onClick={validate} disabled={Boolean(busy)}><ShieldCheck size={16} /> Validate</button><button className="primary" onClick={run} disabled={Boolean(busy)}><Play size={16} fill="currentColor" /> Run</button></div>
      </header>
      <main className="workspace">
        <Palette onAdd={addNode} />
        <section className="canvas-shell">
          <div className="canvas-toolbar"><span><CheckCircle2 size={14} /> Steady-state PFD</span><span className={serviceError ? 'offline' : ''}>{serviceError ? <CloudOff size={14} /> : null}{nodes.length} units · {edges.length} streams</span></div>
          <ReactFlow<PfdNode, PfdEdge> nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={(changes) => { onNodesChange(changes); if (changes.some((change) => change.type === 'position' && change.dragging === false)) markChanged() }} onEdgesChange={(changes) => { onEdgesChange(changes); if (changes.some((change) => change.type === 'remove')) markChanged() }} onConnect={connect} onSelectionChange={({ nodes: selected }) => setSelectedId(selected[0]?.id)} onNodesDelete={(deleted) => deleted.forEach((node) => deleteNode(node.id))} fitView minZoom={0.3} maxZoom={1.8}>
            <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} />
            <MiniMap nodeColor={(node) => node.data?.status === 'invalid' ? '#d06a57' : node.data?.status === 'valid' ? '#55a985' : '#82a8a1'} maskColor="rgba(6, 17, 20, .7)" />
            <Controls />
          </ReactFlow>
        </section>
        <Inspector node={selectedNode} onChange={updateNode} onDelete={deleteNode} />
        <ResultsPanel validation={validation} run={lastRun} previousRun={previousRun} busy={busy} serviceError={serviceError} />
      </main>
    </div>
  )
}

export default function App() { return <ReactFlowProvider><Studio /></ReactFlowProvider> }
