# DW2 additive command fixtures

`commands.json` fixes the tagged wire shape of `draft.create`, `draft.list` and
its catalogue data. Authored 2026-09-11; timestamps/IDs are fixture values, not
runtime observations. Tests compare constructed DTOs against these fixed objects
and decode them back. New command tags leave all DW1 fixtures unchanged; an old
strict codec rejects unknown tags and is not expected to decode these additions.
These are software-contract fixtures, not scientific data or V&V evidence.
