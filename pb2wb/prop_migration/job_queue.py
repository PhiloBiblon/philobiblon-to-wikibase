"""
job_queue.py — run approved FactGrid jobs one after another on the worker box,
continuing only while everything is going well.

Jobs live in prop_migration/jobs/{queue,running,done,failed}/ as small JSON files
({"name", "cmd", "added"}). Only jobs Max has approved are added. The worker takes
the oldest queued job, runs it (log: prop_migration/run_logs/job_<name>.log), and
after each job checks that it went well:

  - exit code 0
  - no read-back / spot-check failures or "failed in a row" stops in its log
  - no low-reputation pauses or bot challenges in the reputation log during the job

If any check fails the job goes to failed/ and the worker stops. It also stops when
the queue is empty or a STOP file exists (finishing the current job first), and it
does not start a job during FactGrid's nightly maintenance (6:50-7:50 pm ET).

Usage (from pb2wb/):
    python prop_migration/job_queue.py add NAME -- python prop_migration/... args
    python prop_migration/job_queue.py status
    python prop_migration/job_queue.py work            # usually inside tmux
    python prop_migration/job_queue.py stop            # finish current job, then stop
In a job command, {python} is replaced by the interpreter running the worker.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

JOBS_DIR       = 'prop_migration/jobs'
LOG_DIR        = 'prop_migration/run_logs'
REPUTATION_LOG = 'prop_migration/run_logs/reputation.jsonl'
STOP_FILE      = os.path.join(JOBS_DIR, 'STOP')
STATES         = ('queue', 'running', 'done', 'failed')

# FactGrid's nightly maintenance is ~7 pm ET; don't start jobs from 6:50 to 7:50 pm ET.
MAINT_START = (18, 50)
MAINT_END   = (19, 50)



# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------

def eastern_now(now_utc=None):
    """Current US Eastern time (EDT/EST by the US DST rule), as a naive datetime."""
    now = now_utc or datetime.now(timezone.utc)
    y = now.year
    # DST: second Sunday in March 2:00 local (7:00 UTC) to first Sunday in Nov 2:00 local (6:00 UTC)
    mar = datetime(y, 3, 8, 7, tzinfo=timezone.utc)
    start = mar + timedelta(days=(6 - mar.weekday()) % 7)
    nov = datetime(y, 11, 1, 6, tzinfo=timezone.utc)
    end = nov + timedelta(days=(6 - nov.weekday()) % 7)
    offset = -4 if start <= now < end else -5
    return (now + timedelta(hours=offset)).replace(tzinfo=None)


def in_maintenance(et):
    hm = (et.hour, et.minute)
    return MAINT_START <= hm < MAINT_END


def log_problems(text):
    """Lines in a job log that mean the job did not go well."""
    out = []
    for line in text.splitlines():
        if re.search(r'READ-BACK FAILED|failed in a row', line):
            out.append(line.strip())
        m = re.search(r'Spot-check: (\d+) OK, (\d+) FAILED, (\d+) errors', line)
        if m and (int(m.group(2)) or int(m.group(3))):
            out.append(line.strip())
    return out


def reputation_problems(lines, since_iso):
    """Low-score pauses or challenges logged at or after since_iso."""
    out = []
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get('ts', '') >= since_iso and r.get('event') in ('low', 'challenge'):
            out.append(f"{r['ts']} {r['event']} {r.get('reputation')}")
    return out


# ---------------------------------------------------------------------------
# Queue operations
# ---------------------------------------------------------------------------

def _dir(state):
    return os.path.join(JOBS_DIR, state)


def _jobs(state):
    d = _dir(state)
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.json'))


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def cmd_add(args):
    for s in STATES:
        os.makedirs(_dir(s), exist_ok=True)
    name = re.sub(r'[^A-Za-z0-9_.-]+', '_', args.name)
    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == '--' else args.cmd
    if not cmd:
        sys.exit('no command given (use: add NAME -- command ...)')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    path = os.path.join(_dir('queue'), f'{stamp}_{name}.json')
    with open(path, 'w') as f:
        json.dump({'name': name, 'cmd': cmd, 'added': _now_iso()}, f, ensure_ascii=False, indent=1)
    print(f'queued: {os.path.basename(path)}')


def cmd_status(args):
    for s in STATES:
        jobs = _jobs(s)
        if s in ('done', 'failed'):
            jobs = jobs[-args.last:]
        print(f'{s:8} {len(_jobs(s)):3}')
        for p in jobs:
            with open(p) as f:
                j = json.load(f)
            extra = ''
            if 'finished' in j:
                extra = f"  finished {j['finished']}  {j.get('result', '')}"
            elif 'started' in j:
                extra = f"  started {j['started']}"
            print(f"         {j['name']}{extra}")
    if os.path.exists(STOP_FILE):
        print('STOP file present: worker will stop after the current job')
    if os.path.exists(REPUTATION_LOG):
        with open(REPUTATION_LOG) as f:
            last = f.readlines()[-1:]
        if last:
            r = json.loads(last[0])
            print(f"last FactGrid request: {r['ts']}  reputation {r['reputation']}  ({r['event']})")


def cmd_stop(args):
    os.makedirs(JOBS_DIR, exist_ok=True)
    open(STOP_FILE, 'w').close()
    print('STOP file written: the worker will stop after the current job')


def _move(path, state, **update):
    with open(path) as f:
        j = json.load(f)
    j.update(update)
    new = os.path.join(_dir(state), os.path.basename(path))
    with open(new, 'w') as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
    os.remove(path)
    return new, j


def cmd_work(args):
    for s in STATES:
        os.makedirs(_dir(s), exist_ok=True)
    if _jobs('running'):
        sys.exit(f'a job is already marked running: {_jobs("running")[0]} — check it before starting')
    print(f'{_now_iso()} worker started')
    while True:
        if os.path.exists(STOP_FILE):
            os.remove(STOP_FILE)
            print(f'{_now_iso()} STOP file found — worker stopping')
            return
        queued = _jobs('queue')
        if not queued:
            print(f'{_now_iso()} queue empty — worker stopping')
            return
        et = eastern_now()
        if in_maintenance(et):
            print(f'{_now_iso()} FactGrid maintenance window ({et:%H:%M} ET) — waiting')
            time.sleep(300)
            continue

        started = _now_iso()
        path, job = _move(queued[0], 'running', started=started)
        logpath = os.path.join(LOG_DIR, f"job_{job['name']}.log")
        cmd = [c.replace('{python}', sys.executable) for c in job['cmd']]
        print(f'{started} START {job["name"]}: {" ".join(shlex.quote(c) for c in cmd)}')
        with open(logpath, 'a') as log:
            rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT)

        problems = [] if rc == 0 else [f'exit code {rc}']
        with open(logpath, errors='replace') as f:
            problems += log_problems(f.read())
        if os.path.exists(REPUTATION_LOG):
            with open(REPUTATION_LOG) as f:
                problems += reputation_problems(f, started)

        finished = _now_iso()
        if problems:
            _move(path, 'failed', finished=finished, result='FAILED', problems=problems[:20])
            print(f'{finished} FAILED {job["name"]} — worker stopping:')
            for p in problems[:20]:
                print(f'    {p}')
            return
        _move(path, 'done', finished=finished, result='ok')
        print(f'{finished} DONE {job["name"]}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    sub = ap.add_subparsers(dest='cmd_name', required=True)
    a = sub.add_parser('add', help='queue an approved job')
    a.add_argument('name')
    a.add_argument('cmd', nargs=argparse.REMAINDER)
    s = sub.add_parser('status', help='show the queue')
    s.add_argument('--last', type=int, default=5, help='how many done/failed jobs to list')
    sub.add_parser('work', help='run queued jobs one by one')
    sub.add_parser('stop', help='stop the worker after the current job')
    args = ap.parse_args()
    {'add': cmd_add, 'status': cmd_status, 'work': cmd_work, 'stop': cmd_stop}[args.cmd_name](args)


if __name__ == '__main__':
    main()
