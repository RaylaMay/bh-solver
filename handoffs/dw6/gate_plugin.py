"""Capture exact collection and every test outcome for the trusted runner."""

from __future__ import annotations

import json
import os
from pathlib import Path

collected: list[str] = []
outcomes: dict[str, str] = {}
collection_errors: list[str] = []


def pytest_collection_finish(session):
    collected.extend(item.nodeid for item in session.items)


def pytest_collectreport(report):
    if report.failed:
        collection_errors.append(report.nodeid)


def pytest_runtest_logreport(report):
    if getattr(report, "wasxfail", None) is not None:
        outcomes[report.nodeid] = "xfail-or-xpass"
    elif report.failed:
        outcomes[report.nodeid] = "failed"
    elif report.skipped:
        outcomes[report.nodeid] = "skipped"
    elif report.when == "call" and report.nodeid not in outcomes:
        outcomes[report.nodeid] = "passed"


def pytest_sessionfinish(session, exitstatus):
    destination = os.environ.get("DW6_GATE_REPORT")
    if destination:
        Path(destination).write_text(
            json.dumps(
                {
                    "collected": collected,
                    "outcomes": outcomes,
                    "collection_errors": collection_errors,
                    "pytest_exit": int(exitstatus),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
