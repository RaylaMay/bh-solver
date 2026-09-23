import json,tempfile,time
from pathlib import Path
from PySide6.QtWidgets import QApplication,QLineEdit
from PySide6.QtCore import QTimer
from bh_sim.adapters.desktop_preview import create_supervised_gateway
from bh_sim.uix.workspace import WorkspaceSettings
from bh_sim.uix.workstation_editor import WorkstationEditor
app=QApplication.instance() or QApplication([])
with tempfile.TemporaryDirectory() as data:
    root=Path(data)
    gateway=create_supervised_gateway(root)
    w=WorkstationEditor(gateway,WorkspaceSettings(root/'ui.ini'))
    w.show();app.processEvents();w.create_draft('InspectorProbe')
    for cmd in ['add source','add heater','add sink','connect Source-001 out-0 Heater-001 in-0','connect Heater-001 out-0 Sink-001 in-0','set Source-001 massFlow 12.5 kg/s','set Source-001 temperature 360 K','set Source-001 pressure 250000 Pa','set Heater-001 duty 75000 W']:
        w.run_command(cmd)
    assert w.validate_current()
    unit=next(e for e in w.document.draft.equipment if e.model_id=='heater')
    w.canvas.select_ids((unit.object_id,));app.processEvents()
    fields={x.accessibleName():x for x in w.input_panel.findChildren(QLineEdit)}
    field=fields['Heat duty value'];field.setText('125000');field.setModified(True)
    engine=gateway.services.engineering
    original_run=engine.run
    def delayed_run(*args,**kwargs):
        time.sleep(0.3)
        return original_run(*args,**kwargs)
    engine.run=delayed_run
    ticks=[]
    QTimer.singleShot(20,lambda:ticks.append(time.monotonic()))
    start=time.monotonic(); result=w.run_current();elapsed=time.monotonic()-start
    unit=next(e for e in w.document.draft.equipment if e.model_id=='heater')
    duty=next(p.quantity.value for p in unit.parameters if p.name=='duty')
    print('PENDING_INSPECTOR_AND_EVENT_LOOP',json.dumps({'requested_duty_W':125000,'draft_duty_after_run_W':duty,'run_success':result,'elapsed_s':round(elapsed,3),'timer_callbacks_during_run':len(ticks),'pending_inputs_after_run':len(w.pending_inputs)}))
    app.processEvents()
    print('TIMER_CALLBACKS_AFTER_EVENT_PROCESSING',len(ticks))
    w.close();app.processEvents()
