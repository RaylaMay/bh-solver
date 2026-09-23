"""Drive the proposed public BH interfaces; never substitute application/solver policy.

Imports of future product capabilities are lazy so all tests collect on pre-DW6
source and fail with a feature-specific assertion rather than an import error.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib
import json
import threading
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from oracles import audit_valid

ROOT = Path(__file__).resolve().parent
SECRET = "sk-dw6-synthetic-secret-never-a-real-key"
MODEL = "dw6-controlled-model"
TERMINAL = {"REVIEW_READY", "COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED", "LIMIT_REACHED"}
LIMITS = {
    "participants": 1,
    "iterations": 5,
    "runs": 5,
    "elapsed_seconds": 300,
    "tokens": 50_000,
    "tool_calls": 20,
    "retries": 0,
}


def plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: plain(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def contract(name: str, *args: Any, **kwargs: Any) -> Any:
    module = importlib.import_module("bh_sim.boundary.contracts")
    constructor = getattr(module, name, None)
    assert constructor is not None, f"DW6_MISSING_CONTRACT: {name} (acceptance spec section 3)"
    if dataclasses.is_dataclass(constructor):
        fields = {field.name for field in dataclasses.fields(constructor)}
        missing = sorted(set(kwargs) - fields)
        assert not missing, f"DW6_MISSING_CONTRACT_FIELDS: {name}: {', '.join(missing)}"
    assert callable(constructor), f"DW6_INVALID_CONTRACT: {name} is not a constructor"
    return constructor(*args, **kwargs)


def response(*, duty: float = 600_000, done: bool = True, kind: str = "proposal") -> dict:
    """Literal test input, not a numerical output or expected solver calculation."""
    return {
        "schema_version": "bh-ai-provider-output-v1",
        "kind": kind,
        "text": "Consider the explicitly bounded heater duty.",
        "rationale": "A synthetic proposal for software verification only.",
        "changes": (
            [
                {
                    "object_id": "heater-1",
                    "parameter": "duty",
                    "before": {"value": 500_000, "unit": "W"},
                    "after": {"value": duty, "unit": "W"},
                }
            ]
            if kind == "proposal"
            else []
        ),
        "claims": [],
        "requested_tools": [],
        "done": done,
    }


class Clock:
    """An externally controlled clock, independent of GUI polling deadlines."""

    def __init__(self) -> None:
        self.offset = 0.0
        self.start = time.monotonic()

    def monotonic(self) -> float:
        return time.monotonic() - self.start + self.offset

    def utc_now(self) -> str:
        return (datetime(2026, 9, 16, tzinfo=UTC) + timedelta(seconds=self.monotonic())).isoformat()

    def advance(self, seconds: float) -> None:
        self.offset += seconds


class Credentials:
    """Test replacement for the OS credential-store boundary, not project storage."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.fail = False

    def get(self, provider_id: str) -> str | None:
        if self.fail:
            raise OSError("Synthetic credential-store failure")
        return self.values.get(provider_id)

    def set(self, provider_id: str, value: str) -> None:
        if self.fail:
            raise OSError("Synthetic credential-store failure")
        self.values[provider_id] = value

    def delete(self, provider_id: str) -> None:
        self.values.pop(provider_id, None)


class Transport(httpx.BaseTransport):
    """Controlled HTTP responses delivered to the actual provider adapter."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.replies: deque[tuple[int, Any]] = deque()
        self.input_tokens = 100
        self.input_usage = 100
        self.output_tokens = 20
        self.return_model = MODEL
        self.include_usage = True
        self.entered = threading.Event()
        self.release = threading.Event()
        self.release.set()
        self.on_generate: Any = None

    def queue(self, body: Any, status: int = 200) -> None:
        self.replies.append((status, body))

    @property
    def generations(self) -> list[dict]:
        return [item for item in self.calls if item["path"] == "/v1/responses"]

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.calls.append(
            {
                "path": request.url.path,
                "body": body,
                "authorization": request.headers.get("authorization"),
            }
        )
        if request.url.path == "/v1/responses/input_tokens":
            return httpx.Response(
                200, json={"object": "response.input_tokens", "input_tokens": self.input_tokens}
            )
        assert request.url.path == "/v1/responses", "Unexpected provider endpoint/tool"
        self.entered.set()
        if self.on_generate:
            self.on_generate()
        assert self.release.wait(10), "Test HTTP boundary was not released"
        assert self.replies, "Candidate made an unexpected extra provider request"
        status, output = self.replies.popleft()
        if isinstance(output, Exception):
            raise output
        if status != 200:
            return httpx.Response(status, json=output)
        if isinstance(output, dict) and output.get("object") == "response":
            return httpx.Response(200, json=output)
        text = output if isinstance(output, str) else json.dumps(output)
        result = {
            "id": f"resp_{len(self.generations)}",
            "object": "response",
            "created_at": 1789516800,
            "status": "completed",
            "model": self.return_model,
            "output": [
                {
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": text, "annotations": []}],
                }
            ],
        }
        if self.include_usage:
            result["usage"] = {
                "input_tokens": self.input_usage,
                "output_tokens": self.output_tokens,
                "total_tokens": self.input_usage + self.output_tokens,
                "output_tokens_details": {"reasoning_tokens": 0},
            }
        return httpx.Response(200, json=result)

    def close(self) -> None:
        self.release.set()


class Client:
    """Only public commands, native actions and artifact exports are used here."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.transport = Transport()
        self.clock = Clock()
        self.credentials = Credentials()
        self._runtime: Any = None
        self.app: Any = None

    @property
    def runtime(self) -> Any:
        if self._runtime is None:
            launcher = importlib.import_module("bh_sim.desktop_launcher")
            factory = getattr(launcher, "create_workstation", None)
            assert callable(factory), (
                "DW6_MISSING_PRODUCTION_FACTORY: desktop_launcher.create_workstation; "
                "the pre-DW6 preview is not an accepted AI/worker implementation"
            )
            try:
                from PySide6.QtWidgets import QApplication
            except ImportError as error:
                raise AssertionError("DW6_REQUIRED_NATIVE_DEPENDENCY: PySide6") from error
            self.app = QApplication.instance() or QApplication([])
            self._runtime = factory(
                self.root,
                ai_transport=self.transport,
                ai_clock=self.clock,
                credential_store=self.credentials,
            )
            assert self._runtime.window is not None and self._runtime.gateway is not None
            self._runtime.window.show()
            self.pump()
        return self._runtime

    @property
    def window(self) -> Any:
        return self.runtime.window

    def pump(self) -> None:
        if self.app:
            self.app.processEvents()

    def close(self) -> None:
        self.transport.release.set()
        if self._runtime is not None:
            self._runtime.close()
            self._runtime = None
            self.pump()

    def call(
        self,
        name: str,
        type_name: str,
        *args: Any,
        request_id: str = "",
        actor: str = "human:reviewer",
        profile: str = "REVIEW",
        **kwargs: Any,
    ) -> Any:
        gateway = self.runtime.gateway
        assert name in gateway.command_names, f"DW6_MISSING_COMMAND: {name}"
        params = contract(type_name, *args, **kwargs)
        return gateway.dispatch(
            contract(
                "CommandRequest", name, request_id or "test:" + uuid4().hex, actor, params, profile
            )
        )

    def ok(self, name: str, type_name: str, *args: Any, **kwargs: Any) -> dict:
        result = self.call(name, type_name, *args, **kwargs)
        assert result.disposition == "COMPLETED", plain(result)
        assert dataclasses.is_dataclass(result.data), "Public output must be a neutral DTO"
        return plain(result.data)

    def configure(self, *, remember: bool = False) -> dict:
        return self.ok(
            "ai.provider.configure", "AiProviderParameters", "openai", MODEL, SECRET, remember
        )

    def seed(self, name: str = "dw6-baseline", *, profile: str = "REVIEW") -> Any:
        """Create a real stored source→heater→sink case through ordinary commands."""
        fixture = json.loads((ROOT / "fixtures/source.json").read_text())
        equipment = tuple(
            contract(
                "EquipmentDto",
                node["id"],
                node["model"],
                tuple(
                    contract(
                        "ParameterDto", key, contract("QuantityDto", item["value"], item["unit"])
                    )
                    for key, item in node["parameters"].items()
                ),
            )
            for node in fixture["equipment"]
        )
        connections = tuple(
            contract("ConnectionDto", item["id"], item["source"], item["target"], "out-0", "in-0")
            for item in fixture["connections"]
        )
        presentation = contract(
            "PresentationDto",
            tuple(
                contract("ObjectPresentationDto", node["id"], node["id"], float(i * 150), 0.0)
                for i, node in enumerate(fixture["equipment"])
            ),
        )
        draft = contract(
            "DraftDto",
            name,
            1,
            None,
            "2026-09-16T00:00:00Z",
            equipment,
            connections,
            presentation,
            profile=profile,
            execution_scope="ordinary",
        )
        imported = self.call("pfd.import", "DraftParameters", draft)
        assert imported.disposition == "COMPLETED", plain(imported)
        started = self.call("history.start", "PfdDocumentParameters", imported.data)
        assert started.disposition == "COMPLETED", plain(started)
        assert self.window.open_draft(name)
        return started.data

    def head(self, name: str = "dw6-baseline") -> dict:
        return self.ok("history.open", "HistoryTarget", name)

    def target(self, name: str = "dw6-baseline") -> Any:
        head = self.head(name)
        return contract("HistoryTarget", name, head["entries"][-1]["entry_id"])

    def preview(
        self,
        *,
        selected: tuple = ("heater-1",),
        attachments: tuple = (),
        name: str = "dw6-baseline",
    ) -> dict:
        return self.ok(
            "ai.context.preview",
            "AiContextParameters",
            self.target(name),
            selected,
            tuple(str(p) for p in attachments),
        )

    def session(self, profile: str = "REVIEW", *, context: dict | None = None) -> dict:
        return self.ok(
            "ai.session.create",
            "AiSessionParameters",
            (context or self.preview())["context_id"],
            profile,
            "Evaluate the selected heater; test fixture only.",
        )

    def inspect(self, session: dict) -> dict:
        return self.ok("ai.session.inspect", "AiSessionTarget", session["session_id"])

    def wait(self, session: dict, states: set[str] = TERMINAL, timeout: float = 12) -> dict:
        deadline = time.monotonic() + timeout
        current = {"state": "NOT_OBSERVED"}
        while time.monotonic() < deadline:
            self.pump()
            current = self.inspect(session)
            if current["state"] in states:
                return current
            time.sleep(0.01)
        raise AssertionError(f"DW6 bounded wait expired; last session state: {current}")

    def send(self, session: dict, reply: Any = None) -> dict:
        if reply is not None:
            self.transport.queue(reply)
        self.ok(
            "ai.session.send", "AiSendParameters", session["session_id"], session["context_hash"]
        )
        return self.wait(session)

    def proposal_target(self, session: dict, index: int = -1) -> Any:
        proposal = session["proposals"][index]
        return contract(
            "AiProposalTarget",
            session["session_id"],
            proposal["proposal_id"],
            proposal["proposal_hash"],
            proposal["source_head"],
        )

    def proposal_action(self, action: str, session: dict, **kwargs: Any) -> Any:
        target = self.proposal_target(session)
        return self.call(
            "ai.proposal." + action, "AiProposalTarget", **dataclasses.asdict(target), **kwargs
        )

    def plan(
        self, session: dict, *, limits: dict | None = None, ranges: tuple | None = None
    ) -> dict:
        if ranges is None:
            ranges = (
                contract(
                    "AiRange",
                    "heater-1",
                    "duty",
                    contract("QuantityDto", 400_000, "W"),
                    contract("QuantityDto", 700_000, "W"),
                ),
            )
        return self.ok(
            "ai.exploration.plan",
            "AiPlanParameters",
            session["session_id"],
            ranges,
            contract("AiBudget", **(limits or LIMITS)),
        )

    def start(self, session: dict, *, plan: dict | None = None) -> dict:
        plan = plan or self.plan(session)
        return self.ok(
            "ai.exploration.start",
            "AiPlanTarget",
            session["session_id"],
            plan["plan_id"],
            plan["plan_hash"],
        )

    def export(self, session: dict) -> dict:
        result = self.ok("ai.session.export", "AiSessionTarget", session["session_id"])
        audit_valid(result)
        return result

    def protected(self) -> dict:
        head = self.head()
        draft_id = head["document"]["draft"]["draft_id"]
        # The retained reference mapping specifies case:<draft_id>.
        result = self.call("run.select_last_valid", "LastValidParameters", "case:" + draft_id)
        assert result.disposition == "COMPLETED", plain(result)
        return {"history": head, "last_valid": plain(result.data)}

    def baseline_run(self, *, profile: str = "REVIEW") -> dict:
        """Ordinary explicit Validate/Run through the production worker gateway."""
        opened = self.call("history.open", "HistoryTarget", "dw6-baseline")
        assert opened.disposition == "COMPLETED", plain(opened)
        draft = opened.data.document.draft
        receipt = self.ok("draft.validate", "DraftParameters", draft, profile=profile)
        attempt = self.ok(
            "run.start", "StartRunParameters", draft, receipt["receipt_id"], profile=profile
        )
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            self.pump()
            result = self.call("run.inspect", "InspectRunParameters", attempt["run_id"])
            if result.disposition == "COMPLETED" and result.data is not None:
                view = plain(result.data)
                if view.get("convergence") == "CONVERGED":
                    return view
            time.sleep(0.01)
        raise AssertionError("Ordinary real-worker baseline did not become inspectable")


def codes(value: Any) -> set[str]:
    data = plain(value)
    found: set[str] = set()
    if isinstance(data, dict):
        if "code" in data:
            found.add(data["code"])
        for child in data.values():
            found.update(codes(child))
    elif isinstance(data, list):
        for child in data:
            found.update(codes(child))
    return found


def clone(value: Any) -> Any:
    return copy.deepcopy(value)
