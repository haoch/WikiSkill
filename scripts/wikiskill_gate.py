#!/usr/bin/env python3
"""Deterministic accept/rollback gate for a WikiSkill domain workspace.

The whole point of this script existing (rather than asking an agent to decide) is that
acceptance must be an objective, reproducible numeric comparison: candidate validation score vs.
the best score accepted so far, strictly greater to accept. See reference/architecture.md for
the state.json and snapshot layout this manages.

Usage:
  wikiskill_gate.py baseline --project-root P --domain D --skill-prefix PRE --val-score 0.5 --val-fraction "3/6"
  wikiskill_gate.py gate     --project-root P --domain D --skill-prefix PRE --val-score 0.66 --val-fraction "4/6"

Both subcommands print one JSON line to stdout describing the resulting state.
"""
import argparse
import glob
import json
import os
import shutil
import sys


def workspace_dir(project_root, domain):
    return os.path.join(project_root, ".wikiskill", domain)


def state_path(project_root, domain):
    return os.path.join(workspace_dir(project_root, domain), "state.json")


def snapshot_dir(project_root, domain):
    return os.path.join(workspace_dir(project_root, domain), "snapshots", "accepted")


def live_skills_root(project_root):
    return os.path.join(project_root, ".claude", "skills")


def live_skill_dirs(project_root, skill_prefix):
    pattern = os.path.join(live_skills_root(project_root), skill_prefix + "-*")
    return sorted(d for d in glob.glob(pattern) if os.path.isdir(d))


def load_state(project_root, domain):
    path = state_path(project_root, domain)
    if not os.path.exists(path):
        return {"best_val_score": None, "best_val_fraction": None, "iteration": 0, "history": []}
    with open(path) as f:
        return json.load(f)


def save_state(project_root, domain, state):
    path = state_path(project_root, domain)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def replace_dir(dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)


def snapshot_live_skills(project_root, domain, skill_prefix):
    """Copy the current live skill dirs into snapshots/accepted/, replacing any prior snapshot."""
    snap = snapshot_dir(project_root, domain)
    replace_dir(snap)
    os.makedirs(snap, exist_ok=True)
    for src in live_skill_dirs(project_root, skill_prefix):
        shutil.copytree(src, os.path.join(snap, os.path.basename(src)))


def restore_live_skills_from_snapshot(project_root, domain, skill_prefix):
    """Remove current live skill dirs for this domain and restore from the last accepted snapshot."""
    for d in live_skill_dirs(project_root, skill_prefix):
        shutil.rmtree(d)
    snap = snapshot_dir(project_root, domain)
    if not os.path.isdir(snap):
        return  # no prior accepted snapshot (baseline was empty) -> live root stays empty
    os.makedirs(live_skills_root(project_root), exist_ok=True)
    for name in sorted(os.listdir(snap)):
        src = os.path.join(snap, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(live_skills_root(project_root), name))


def cmd_baseline(args):
    state = {
        "best_val_score": args.val_score,
        "best_val_fraction": args.val_fraction,
        "iteration": 0,
        "history": [{"iteration": 0, "val_score": args.val_score, "outcome": "baseline"}],
    }
    snapshot_live_skills(args.project_root, args.domain, args.skill_prefix)
    save_state(args.project_root, args.domain, state)
    print(json.dumps({"outcome": "baseline", "best_val_score": args.val_score, "iteration": 0}))


def cmd_gate(args):
    state = load_state(args.project_root, args.domain)
    if state["best_val_score"] is None:
        print(
            "error: no state.json / baseline found — run the 'baseline' subcommand once "
            "before the first gated iteration",
            file=sys.stderr,
        )
        sys.exit(1)

    iteration = state["iteration"] + 1
    if args.val_score > state["best_val_score"]:
        outcome = "accepted"
        snapshot_live_skills(args.project_root, args.domain, args.skill_prefix)
        state["best_val_score"] = args.val_score
        state["best_val_fraction"] = args.val_fraction
    else:
        outcome = "rejected"
        restore_live_skills_from_snapshot(args.project_root, args.domain, args.skill_prefix)

    state["iteration"] = iteration
    state["history"].append(
        {"iteration": iteration, "val_score": args.val_score, "outcome": outcome}
    )
    save_state(args.project_root, args.domain, state)
    print(
        json.dumps(
            {
                "outcome": outcome,
                "best_val_score": state["best_val_score"],
                "iteration": iteration,
                "early_stop": state["best_val_score"] >= 1.0,
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project-root", required=True, help="user project root (contains .claude/ and .wikiskill/)")
    common.add_argument("--domain", required=True)
    common.add_argument("--skill-prefix", required=True, help="e.g. wikiskill-<domain>")
    common.add_argument("--val-score", required=True, type=float, help="0..1 fraction pass on val split")
    common.add_argument("--val-fraction", required=True, help="human-readable e.g. '5/6'")

    p_baseline = sub.add_parser("baseline", parents=[common])
    p_baseline.set_defaults(func=cmd_baseline)

    p_gate = sub.add_parser("gate", parents=[common])
    p_gate.set_defaults(func=cmd_gate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
