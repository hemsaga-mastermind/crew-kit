"""Acceptance tests for the Crew Kit v0.3 engine (SPEC-0.3.md).

Committed before the implementation, as protocol rule 11 requires.
Run: python3 -I -m unittest discover -s tests -t .
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crewkit import cli  # noqa: E402
from tests import workspace as ws  # noqa: E402

ASOF = "2026-10-21"


def run(args):
    """Run the CLI, return (exit code, parsed JSON)."""
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(list(args) + ["--json"])
    text = out.getvalue()
    try:
        return code, json.loads(text)
    except json.JSONDecodeError:
        raise AssertionError("not JSON on stdout:\n" + text)


def checks(result, agent_id):
    for a in result["agents"]:
        if a["id"] == agent_id:
            return {c["id"]: c for c in a["checks"]}
    raise AssertionError("no agent %r in %r" % (agent_id, result))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def health(self, extra=()):
        return run(["health", str(self.root), "--asof", ASOF] + list(extra))


class TestVerdictModel(Base):
    def test_only_three_verdicts_ever_appear(self):
        ws.healthy(self.root)
        _, res = self.health()
        seen = {c["verdict"] for a in res["agents"] for c in a["checks"]}
        self.assertTrue(seen <= {"pass", "fail", "unknown"}, seen)

    def test_every_check_names_the_path_it_used(self):
        ws.healthy(self.root)
        _, res = self.health()
        for a in res["agents"]:
            for c in a["checks"]:
                self.assertIn("evidence", c)
                self.assertIn("detail", c)

    def test_result_carries_coverage(self):
        ws.healthy(self.root)
        _, res = self.health()
        self.assertIn("read", res["coverage"])
        self.assertIn("unreadable", res["coverage"])
        self.assertIn("asof", res)
        self.assertEqual(res["asof"], ASOF)
        self.assertEqual(res["crew_kit"], "0.3")


class TestHealth(Base):
    def test_healthy_workspace_is_amber_not_green_because_slips_are_unknown(self):
        ws.healthy(self.root)
        code, res = self.health()
        c = checks(res, "operator")
        self.assertEqual(c["state_fresh"]["verdict"], "pass")
        self.assertEqual(c["status_sent"]["verdict"], "pass")
        self.assertEqual(c["backlog_overdue"]["verdict"], "pass")
        self.assertEqual(c["handoff_answered"]["verdict"], "pass")
        self.assertEqual(c["rule_slips"]["verdict"], "unknown")
        self.assertEqual(res["agents"][0]["colour"], "amber")
        self.assertEqual(code, 0, "unknown alone must not be a failure exit")

    def test_stale_state_fails(self):
        ws.healthy(self.root)
        ws.write(self.root / "agents/operator/state.md", ws.STATE.format(updated="2026-10-01"))
        code, res = self.health()
        self.assertEqual(checks(res, "operator")["state_fresh"]["verdict"], "fail")
        self.assertEqual(res["agents"][0]["colour"], "red")
        self.assertEqual(code, 1)

    def test_state_updated_in_the_future_fails(self):
        ws.healthy(self.root)
        ws.write(self.root / "agents/operator/state.md", ws.STATE.format(updated="2026-12-01"))
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["state_fresh"]["verdict"], "fail")

    def test_missing_state_is_unknown_not_fail(self):
        ws.healthy(self.root)
        os.remove(self.root / "agents/operator/state.md")
        code, res = self.health()
        c = checks(res, "operator")["state_fresh"]
        self.assertEqual(c["verdict"], "unknown")
        self.assertEqual(code, 0)
        self.assertEqual(res["agents"][0]["colour"], "amber")

    def test_unparseable_state_header_is_unknown(self):
        ws.healthy(self.root)
        ws.write(self.root / "agents/operator/state.md", "---\nagent operator\nstatus: green\n---\n")
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["state_fresh"]["verdict"], "unknown")

    def test_duplicate_header_key_is_unknown(self):
        ws.healthy(self.root)
        ws.write(
            self.root / "agents/operator/state.md",
            "---\nagent: operator\nagent: other\nstatus: green\nupdated: %s\n---\n" % ASOF,
        )
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["state_fresh"]["verdict"], "unknown")

    def test_unknown_header_key_is_unknown(self):
        ws.healthy(self.root)
        ws.write(
            self.root / "agents/operator/state.md",
            "---\nagent: operator\nstatus: green\nupdated: %s\nmood: fine\n---\n" % ASOF,
        )
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["state_fresh"]["verdict"], "unknown")

    def test_no_status_this_week_fails(self):
        ws.healthy(self.root)
        os.remove(self.root / ("agents/operator/status/%s.md" % ASOF))
        ws.write(self.root / "agents/operator/status/2026-09-30.md", ws.STATUS.format(date="2026-09-30"))
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["status_sent"]["verdict"], "fail")

    def test_status_missing_a_required_line_does_not_count(self):
        ws.healthy(self.root)
        ws.write(
            self.root / ("agents/operator/status/%s.md" % ASOF),
            "STATUS operator %s\nDone: x\nNext: y\nBlocked: none\nRisks: none\n" % ASOF,
        )
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["status_sent"]["verdict"], "fail")

    def test_backlog_item_overdue_by_more_than_seven_days_fails(self):
        ws.healthy(self.root)
        ws.write(
            self.root / "agents/operator/backlog.md",
            "- [ ] 12 | owner: operator | due: 2026-10-10 | Late item\n",
        )
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["backlog_overdue"]["verdict"], "fail")

    def test_backlog_item_overdue_by_less_than_seven_days_passes(self):
        ws.healthy(self.root)
        ws.write(
            self.root / "agents/operator/backlog.md",
            "- [ ] 12 | owner: operator | due: 2026-10-18 | Slightly late\n",
        )
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["backlog_overdue"]["verdict"], "pass")

    def test_done_items_are_never_overdue(self):
        ws.healthy(self.root)
        ws.write(
            self.root / "agents/operator/backlog.md",
            "- [x] 11 | owner: operator | due: 2026-09-01 | done: 2026-09-02 | Old but done\n",
        )
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["backlog_overdue"]["verdict"], "pass")

    def test_unparseable_backlog_line_makes_overdue_unknown(self):
        ws.healthy(self.root)
        ws.write(self.root / "agents/operator/backlog.md", "- [ ] something informal\n")
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["backlog_overdue"]["verdict"], "unknown")

    def test_handoff_unanswered_after_48_hours_fails(self):
        ws.healthy(self.root)
        ws.write(self.root / "handoffs/h1.md", ws.HANDOFF.format(sent="2026-10-15", answered=""))
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["handoff_answered"]["verdict"], "fail")

    def test_handoff_sent_yesterday_is_not_yet_late(self):
        ws.healthy(self.root)
        ws.write(self.root / "handoffs/h1.md", ws.HANDOFF.format(sent="2026-10-20", answered=""))
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["handoff_answered"]["verdict"], "pass")

    def test_answered_handoff_passes(self):
        ws.healthy(self.root)
        ws.write(
            self.root / "handoffs/h1.md",
            ws.HANDOFF.format(sent="2026-10-01", answered="answered: 2026-10-02\n"),
        )
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["handoff_answered"]["verdict"], "pass")

    def test_handoff_to_another_agent_is_not_this_agents_problem(self):
        ws.healthy(self.root)
        text = ws.HANDOFF.format(sent="2026-10-01", answered="").replace("to: operator", "to: builder")
        ws.write(self.root / "handoffs/h1.md", text)
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["handoff_answered"]["verdict"], "pass")

    def test_slips_file_present_is_read(self):
        ws.healthy(self.root)
        ws.write(self.root / "agents/operator/slips.jsonl", "")
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["rule_slips"]["verdict"], "pass")
        ws.write(
            self.root / "agents/operator/slips.jsonl",
            json.dumps({"date": "2026-10-19", "rule": 3, "what": "prepared an invoice"}) + "\n",
        )
        _, res = self.health()
        self.assertEqual(checks(res, "operator")["rule_slips"]["verdict"], "fail")

    def test_strict_turns_unknown_into_a_failing_exit(self):
        ws.healthy(self.root)
        code, _ = self.health(["--strict"])
        self.assertEqual(code, 1)

    def test_agents_are_sorted_by_id(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["agents"] = [
            {"id": "zeta", "folder": "agents/zeta", "autonomy": "A"},
            {"id": "alpha", "folder": "agents/alpha", "autonomy": "A"},
        ]
        ws.workspace(self.root, man)
        _, res = self.health()
        self.assertEqual([a["id"] for a in res["agents"]], ["alpha", "zeta"])


class TestDeterminism(Base):
    def test_same_input_same_bytes(self):
        ws.healthy(self.root)
        first = io.StringIO()
        with redirect_stdout(first):
            cli.main(["health", str(self.root), "--asof", ASOF, "--json"])
        second = io.StringIO()
        with redirect_stdout(second):
            cli.main(["health", str(self.root), "--asof", ASOF, "--json"])
        self.assertEqual(first.getvalue(), second.getvalue())
        self.assertNotIn("T", first.getvalue().split('"asof"')[1][:30], "no wall clock in the body")

    def test_engine_writes_nothing(self):
        ws.healthy(self.root)
        before = {p: p.stat().st_mtime_ns for p in sorted(self.root.rglob("*")) if p.is_file()}
        for cmd in ("health", "lint", "gates", "verify"):
            run([cmd, str(self.root), "--asof", ASOF])
        after = {p: p.stat().st_mtime_ns for p in sorted(self.root.rglob("*")) if p.is_file()}
        self.assertEqual(before, after)


class TestManifest(Base):
    def bad(self, manifest):
        ws.write(self.root / "crew.json", json.dumps(manifest))
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["health", str(self.root), "--asof", ASOF, "--json"])
        return code, out.getvalue()

    def test_missing_manifest_exits_two(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["health", str(self.root), "--asof", ASOF, "--json"])
        self.assertEqual(code, 2)

    def test_wrong_version_exits_two(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["crew_kit"] = "0.2"
        code, text = self.bad(man)
        self.assertEqual(code, 2)
        self.assertIn("crew_kit", text)

    def test_unknown_key_exits_two(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["mood"] = "fine"
        self.assertEqual(self.bad(man)[0], 2)

    def test_unknown_agent_key_exits_two(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["agents"][0]["mood"] = "fine"
        self.assertEqual(self.bad(man)[0], 2)

    def test_duplicate_agent_id_exits_two(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["agents"].append(dict(man["agents"][0]))
        self.assertEqual(self.bad(man)[0], 2)

    def test_bad_autonomy_exits_two(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["agents"][0]["autonomy"] = "D"
        self.assertEqual(self.bad(man)[0], 2)

    def test_unknown_control_exits_two(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["agents"][0]["controls"] = ["vibes"]
        self.assertEqual(self.bad(man)[0], 2)

    def test_folder_outside_the_workspace_exits_two(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["agents"][0]["folder"] = "../elsewhere"
        self.assertEqual(self.bad(man)[0], 2)


class TestLint(Base):
    def codes(self, agent_id="operator"):
        _, res = run(["lint", str(self.root)])
        return sorted(f["code"] for f in res["findings"] if f["agent"] == agent_id)

    def test_healthy_workspace_has_no_findings(self):
        ws.healthy(self.root)
        code, res = run(["lint", str(self.root)])
        self.assertEqual(res["findings"], [])
        self.assertEqual(code, 0)

    def test_missing_files_are_reported(self):
        ws.healthy(self.root)
        for name in ("state.md", "backlog.md", "charter.md"):
            os.remove(self.root / "agents/operator" / name)
        self.assertEqual(self.codes(), ["L01", "L02", "L03"])

    def test_unparseable_and_incomplete_backlog_lines(self):
        ws.healthy(self.root)
        ws.write(
            self.root / "agents/operator/backlog.md",
            "- [ ] nonsense\n- [ ] 13 | owner: operator | Ship it\n",
        )
        self.assertEqual(self.codes(), ["L04", "L05"])

    def test_handoff_to_a_lane_nothing_wakes(self):
        ws.healthy(self.root)
        text = ws.HANDOFF.format(sent="2026-10-20", answered="").replace("to: operator", "to: ghost")
        ws.write(self.root / "handoffs/h1.md", text)
        _, res = run(["lint", str(self.root)])
        self.assertIn("L06", [f["code"] for f in res["findings"]])

    def test_level_b_without_the_six_controls_names_each_missing_one(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["agents"][0]["autonomy"] = "B"
        man["agents"][0]["controls"] = ["branch_protection", "ci_gates"]
        ws.healthy(self.root)
        ws.write(self.root / "crew.json", json.dumps(man))
        _, res = run(["lint", str(self.root)])
        found = [f for f in res["findings"] if f["code"] == "L07"]
        self.assertEqual(len(found), 1)
        for missing in ("monitoring", "rollback", "kill_switch", "budgets"):
            self.assertIn(missing, found[0]["detail"])

    def test_level_b_with_all_six_controls_is_clean(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["agents"][0]["autonomy"] = "B"
        man["agents"][0]["controls"] = [
            "branch_protection", "ci_gates", "monitoring", "rollback", "kill_switch", "budgets",
        ]
        ws.healthy(self.root)
        ws.write(self.root / "crew.json", json.dumps(man))
        self.assertNotIn("L07", self.codes())

    def test_irreversible_action_with_no_gate(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        man["agents"][0]["actions"] = [
            {"name": "place an order", "irreversible": True, "gate": "none"},
            {"name": "draft a post", "irreversible": True, "gate": "founder"},
        ]
        ws.healthy(self.root)
        ws.write(self.root / "crew.json", json.dumps(man))
        found = [f for f in run(["lint", str(self.root)])[1]["findings"] if f["code"] == "L08"]
        self.assertEqual(len(found), 1)
        self.assertIn("place an order", found[0]["detail"])

    def test_agent_with_no_wakes(self):
        man = json.loads(json.dumps(ws.MANIFEST))
        del man["agents"][0]["wakes"]
        ws.healthy(self.root)
        ws.write(self.root / "crew.json", json.dumps(man))
        self.assertIn("L09", self.codes())

    def test_findings_are_sorted_and_exit_one(self):
        ws.healthy(self.root)
        os.remove(self.root / "agents/operator/state.md")
        code, res = run(["lint", str(self.root)])
        self.assertEqual(code, 1)
        keys = [(f["agent"], f["code"]) for f in res["findings"]]
        self.assertEqual(keys, sorted(keys))


class TestContract(Base):
    """The mutual contract: a contract naming no oracle is invalid."""

    def codes(self, agent_id="operator"):
        _, res = run(["lint", str(self.root)])
        return sorted(f["code"] for f in res["findings"] if f["agent"] == agent_id)

    def test_a_complete_contract_is_clean(self):
        ws.healthy(self.root)
        self.assertEqual(self.codes(), [])

    def test_missing_contract_is_reported(self):
        ws.healthy(self.root)
        os.remove(self.root / "agents/operator/contract.md")
        self.assertEqual(self.codes(), ["L10"])

    def test_missing_section_names_the_section(self):
        ws.healthy(self.root)
        text = ws.CONTRACT.format(extra="")
        text = text.split("## Breach")[0]
        ws.write(self.root / "agents/operator/contract.md", text)
        _, res = run(["lint", str(self.root)])
        found = [f for f in res["findings"] if f["code"] == "L11"]
        self.assertEqual(len(found), 1)
        self.assertIn("Breach", found[0]["detail"])

    def test_a_deliverable_with_no_oracle_is_reported(self):
        ws.healthy(self.root)
        ws.write(
            self.root / "agents/operator/contract.md",
            ws.CONTRACT.format(extra="- a weekly summary for the founder\n"),
        )
        _, res = run(["lint", str(self.root)])
        found = [f for f in res["findings"] if f["code"] == "L12"]
        self.assertEqual(len(found), 1)
        self.assertIn("weekly summary", found[0]["detail"])
        self.assertIn("may not act autonomously", found[0]["detail"])

    def test_an_empty_oracle_is_no_oracle(self):
        ws.healthy(self.root)
        ws.write(
            self.root / "agents/operator/contract.md",
            "# Contract: operator\n\n## I deliver\n- a report, judged by:   \n\n"
            "## I am owed\n- x\n\n## Done means\n- y\n\n## If I cannot\n- z\n\n## Breach\n- w\n",
        )
        self.assertIn("L12", self.codes())

    def test_no_deliverable_at_all_is_reported(self):
        ws.healthy(self.root)
        ws.write(
            self.root / "agents/operator/contract.md",
            "# Contract: operator\n\n## I deliver\n\n## I am owed\n- x\n\n## Done means\n- y\n\n"
            "## If I cannot\n- z\n\n## Breach\n- w\n",
        )
        self.assertIn("L12", self.codes())


class TestPlacement(Base):
    """Capability-based placement."""

    def with_nodes(self, nodes=None, needs=None):
        man = json.loads(json.dumps(ws.MANIFEST))
        if needs is not None:
            man["agents"][0]["needs"] = needs
        ws.healthy(self.root)
        ws.write(self.root / "crew.json", json.dumps(man))
        if nodes is not None:
            ws.write(self.root / "nodes.json", json.dumps(nodes))
        return run(["lint", str(self.root)])

    def test_one_node_default_needs_no_nodes_file(self):
        code, res = self.with_nodes()
        self.assertEqual(res["findings"], [])
        self.assertEqual(code, 0)

    def test_a_need_with_no_nodes_file_is_reported(self):
        _, res = self.with_nodes(needs=["may_send_mail"])
        self.assertEqual([f["code"] for f in res["findings"]], ["L13"])

    def test_a_need_a_node_satisfies_is_clean(self):
        _, res = self.with_nodes(nodes=ws.NODES, needs=["may_send_mail", "always_on"])
        self.assertEqual(res["findings"], [])

    def test_a_need_no_node_satisfies_names_the_capability(self):
        _, res = self.with_nodes(nodes=ws.NODES, needs=["may_hold_personal_data"])
        found = [f for f in res["findings"] if f["code"] == "L13"]
        self.assertEqual(len(found), 1)
        self.assertIn("may_hold_personal_data", found[0]["detail"])

    def test_a_permission_declared_as_a_capability_is_reported(self):
        nodes = json.loads(json.dumps(ws.NODES))
        nodes["nodes"][0]["capabilities"]["may_hold_personal_data"] = True
        _, res = self.with_nodes(nodes=nodes, needs=["may_hold_personal_data"])
        codes = [f["code"] for f in res["findings"]]
        self.assertIn("L14", codes)
        self.assertIn("L13", codes, "a self-declared permission must not satisfy a need")
        found = [f for f in res["findings"] if f["code"] == "L14"][0]
        self.assertIn("grants", found["detail"])

    def test_a_false_grant_does_not_satisfy_a_need(self):
        nodes = json.loads(json.dumps(ws.NODES))
        nodes["nodes"][0]["grants"]["may_send_mail"] = False
        _, res = self.with_nodes(nodes=nodes, needs=["may_send_mail"])
        self.assertIn("L13", [f["code"] for f in res["findings"]])

    def test_an_unknown_capability_in_needs_exits_two(self):
        out = io.StringIO()
        man = json.loads(json.dumps(ws.MANIFEST))
        man["agents"][0]["needs"] = ["vibes"]
        ws.healthy(self.root)
        ws.write(self.root / "crew.json", json.dumps(man))
        with redirect_stdout(out):
            code = cli.main(["lint", str(self.root), "--json"])
        self.assertEqual(code, 2)

    def test_a_broken_nodes_file_exits_two(self):
        ws.healthy(self.root)
        ws.write(self.root / "nodes.json", "{not json")
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["lint", str(self.root), "--json"])
        self.assertEqual(code, 2, "placement the engine cannot trust is fatal, like the manifest")

    def test_an_unknown_node_key_exits_two(self):
        nodes = json.loads(json.dumps(ws.NODES))
        nodes["nodes"][0]["mood"] = "fine"
        out = io.StringIO()
        ws.healthy(self.root)
        ws.write(self.root / "nodes.json", json.dumps(nodes))
        with redirect_stdout(out):
            code = cli.main(["lint", str(self.root), "--json"])
        self.assertEqual(code, 2)


class TestGates(Base):
    LINE = {
        "product": "example",
        "gate": "G1",
        "kill_line": "fewer than 3 people use it within 60 days of publishing",
        "kill_line_written": "2026-01-05",
        "test_started": "2026-01-12",
        "status": "open",
    }

    def gates(self, *records):
        ws.healthy(self.root)
        ws.write(
            self.root / "records/gates.jsonl",
            "".join(json.dumps(r) + "\n" for r in records),
        )
        return run(["gates", str(self.root), "--asof", ASOF])

    def test_pre_registered_kill_line_passes(self):
        code, res = self.gates(self.LINE)
        row = res["gates"][0]
        self.assertEqual(row["checks"]["kill_line_present"]["verdict"], "pass")
        self.assertEqual(row["checks"]["pre_registered"]["verdict"], "pass")
        self.assertEqual(code, 0)

    def test_kill_line_written_after_the_test_started_fails(self):
        late = dict(self.LINE, kill_line_written="2026-01-13")
        code, res = self.gates(late)
        self.assertEqual(res["gates"][0]["checks"]["pre_registered"]["verdict"], "fail")
        self.assertEqual(code, 1)

    def test_same_day_counts_as_pre_registered(self):
        same = dict(self.LINE, kill_line_written="2026-01-12")
        _, res = self.gates(same)
        self.assertEqual(res["gates"][0]["checks"]["pre_registered"]["verdict"], "pass")

    def test_test_not_started_is_unknown(self):
        pending = dict(self.LINE)
        del pending["test_started"]
        code, res = self.gates(pending)
        self.assertEqual(res["gates"][0]["checks"]["pre_registered"]["verdict"], "unknown")
        self.assertEqual(code, 0)

    def test_empty_kill_line_fails(self):
        _, res = self.gates(dict(self.LINE, kill_line="  "))
        self.assertEqual(res["gates"][0]["checks"]["kill_line_present"]["verdict"], "fail")

    def test_bad_gate_name_is_an_error_row(self):
        code, res = self.gates(dict(self.LINE, gate="G9"))
        self.assertEqual(code, 1)
        self.assertTrue(res["errors"])

    def test_missing_gates_file_is_unknown_not_empty_pass(self):
        ws.healthy(self.root)
        os.remove(self.root / "records/gates.jsonl")
        code, res = run(["gates", str(self.root), "--asof", ASOF])
        self.assertEqual(res["gates"], [])
        self.assertIn(str(self.root / "records/gates.jsonl"), " ".join(res["coverage"]["unreadable"]))
        self.assertEqual(code, 0)


class TestVerify(Base):
    REC = {
        "id": "D-2026-10-18-01",
        "date": "2026-10-18",
        "kind": "founder",
        "text": "Build Crew Kit v0.3 as the backbone.",
        "source": {"type": "founder_session", "ref": "evening"},
    }

    def journal(self, text):
        ws.healthy(self.root)
        ws.write(self.root / "records/decisions.jsonl", text)
        return run(["verify", str(self.root)])

    @staticmethod
    def chain(records):
        import hashlib
        lines, prev = [], None
        for rec in records:
            rec = dict(rec, prev=prev)
            body = json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            rec["hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
            prev = rec["hash"]
            lines.append(json.dumps(rec))
        return "".join(line + "\n" for line in lines)

    def test_schema_errors_fail(self):
        bad = dict(self.REC)
        del bad["text"]
        code, res = self.journal(json.dumps(bad) + "\n")
        self.assertEqual(res["checks"]["schema"]["verdict"], "fail")
        self.assertEqual(code, 1)

    def test_valid_but_unchained_journal_is_unknown_not_pass(self):
        code, res = self.journal(json.dumps(self.REC) + "\n")
        self.assertEqual(res["checks"]["schema"]["verdict"], "pass")
        self.assertEqual(res["checks"]["chain"]["verdict"], "unknown")
        self.assertIn("not chained", res["checks"]["chain"]["detail"])
        self.assertEqual(code, 0)

    def test_a_correct_chain_passes(self):
        second = dict(self.REC, id="D-2026-10-19-01", date="2026-10-19", text="Second decision.")
        code, res = self.journal(self.chain([self.REC, second]))
        self.assertEqual(res["checks"]["chain"]["verdict"], "pass")
        self.assertEqual(code, 0)

    def test_an_edited_record_breaks_the_chain_and_names_the_line(self):
        second = dict(self.REC, id="D-2026-10-19-01", date="2026-10-19", text="Second decision.")
        text = self.chain([self.REC, second]).splitlines()
        first = json.loads(text[0])
        first["text"] = "Quietly reworded afterwards."
        code, res = self.journal(json.dumps(first) + "\n" + text[1] + "\n")
        self.assertEqual(res["checks"]["chain"]["verdict"], "fail")
        self.assertIn("line 1", res["checks"]["chain"]["detail"])
        self.assertEqual(code, 1)

    def test_partly_chained_journal_fails(self):
        second = dict(self.REC, id="D-2026-10-19-01", date="2026-10-19", text="Second decision.")
        text = self.chain([self.REC, second]).splitlines()
        code, res = self.journal(text[0] + "\n" + json.dumps(second) + "\n")
        self.assertEqual(res["checks"]["chain"]["verdict"], "fail")
        self.assertEqual(code, 1)

    def test_missing_journal_is_unknown(self):
        ws.healthy(self.root)
        os.remove(self.root / "records/decisions.jsonl")
        code, res = run(["verify", str(self.root)])
        self.assertEqual(res["checks"]["schema"]["verdict"], "unknown")
        self.assertEqual(code, 0)


class TestExample(unittest.TestCase):
    """The worked example in examples/crew is what the README points a reader at."""

    root = Path(__file__).resolve().parents[1] / "examples/crew"

    def test_example_lints_clean(self):
        code, res = run(["lint", str(self.root)])
        self.assertEqual(res["findings"], [], res["findings"])
        self.assertEqual(code, 0)

    def test_example_health_runs_at_its_recorded_asof(self):
        asof = (self.root / "asof.txt").read_text(encoding="utf-8").strip()
        code, res = run(["health", str(self.root), "--asof", asof])
        colours = {a["id"]: a["colour"] for a in res["agents"]}
        self.assertEqual(colours, {"builder": "red", "operator": "amber"})
        self.assertEqual(code, 1)

    def test_example_gates_and_journal(self):
        self.assertEqual(run(["gates", str(self.root), "--asof", "2026-10-21"])[0], 0)
        _, res = run(["verify", str(self.root)])
        self.assertEqual(res["checks"]["chain"]["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
