import tempfile,json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from bh_sim.adapters.desktop_preview import create_supervised_gateway
from bh_sim.uix.workspace import WorkspaceSettings
from bh_sim.uix.workstation_editor import WorkstationEditor
app=QApplication([])
with tempfile.TemporaryDirectory() as data:
 p=Path(data);g=create_supervised_gateway(p);w=WorkstationEditor(g,WorkspaceSettings(p/'ui.ini'));w.show();w.create_draft('A')
 for cmd in ('add source','add heater','add sink','connect Source-001 out-0 Heater-001 in-0','connect Heater-001 out-0 Sink-001 in-0','set Source-001 massFlow 12.5 kg/s','set Source-001 temperature 360 K','set Source-001 pressure 250000 Pa','set Heater-001 duty 75000 W'):w.run_command(cmd)
 assert w.validate_current() and w.run_current();run=w.last_run_view.run_id
 w.run_command('set Heater-001 duty 125000 W');print(json.dumps({'point':'edit','dirty':w.dirty,'stale_label':w.workbook_view.stale_label.text(),'visible':w.workbook_view.stale_label.isVisible()}))
 assert w.save_current();print(json.dumps({'point':'save','dirty':w.dirty,'stale_label':w.workbook_view.stale_label.text(),'visible':w.workbook_view.stale_label.isVisible(),'run_unchanged':w.last_run_view.run_id==run,'workbook_run':w.session.workbook.run_id,'receipt':w.last_receipt}))
 w.close()
