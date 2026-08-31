#!/usr/bin/env python3
"""Budget-constrained, stratified pass/fail sampling of one iteration's raw traces.

Prevents the Wiki Maintainer's context from overflowing on a large training split by picking at
most --max-pass passing traces and --max-fail failing traces, deterministically (seeded by the
iteration number so re-runs against the same raw traces pick the same sample).

Usage:
  wikiskill_sample.py --domain-workspace .wikiskill/my-domain --iteration 3 \
      [--split train] [--max-pass 3] [--max-fail 5]

Prints one absolute file path per line, failing traces first (they're usually more informative).
"""
import argparse
import glob
import json
import os
import random
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain-workspace", required=True)
    parser.add_argument("--iteration", required=True, type=int)
    parser.add_argument("--split", default="train")
    parser.add_argument("--max-pass", type=int, default=3)
    parser.add_argument("--max-fail", type=int, default=5)
    args = parser.parse_args()

    iter_dir = os.path.join(args.domain_workspace, "raw", "iter-%d" % args.iteration)
    if not os.path.isdir(iter_dir):
        print("error: no such iteration dir: %s" % iter_dir, file=sys.stderr)
        sys.exit(1)

    passes, fails = [], []
    for path in sorted(glob.glob(os.path.join(iter_dir, "*.json"))):
        with open(path) as f:
            trace = json.load(f)
        if trace.get("split") != args.split:
            continue
        (passes if trace.get("grade", {}).get("pass") else fails).append(path)

    rng = random.Random(args.iteration)
    sampled_fails = fails if len(fails) <= args.max_fail else rng.sample(fails, args.max_fail)
    sampled_passes = passes if len(passes) <= args.max_pass else rng.sample(passes, args.max_pass)

    for path in sorted(sampled_fails) + sorted(sampled_passes):
        print(path)


if __name__ == "__main__":
    main()
