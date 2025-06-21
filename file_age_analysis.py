import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

def human_readable_delta(delta):
    days = delta.days
    secs = delta.seconds
    hours = secs // 3600
    mins = (secs % 3600) // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    if not parts:
        parts.append(f"{secs}s")
    return ' '.join(parts)

def scan_files(root, include_dirs=False):
    path = Path(root)
    if not path.exists():
        print(f"Error: Path '{root}' does not exist.", file=sys.stderr)
        sys.exit(1)

    entries = []
    for p in path.rglob('*'):
        if not include_dirs and p.is_dir():
            continue
        try:
            stat = p.stat()
            entries.append((p, stat))
        except Exception as e:
            print(f"Warning: Could not stat '{p}': {e}", file=sys.stderr)
    return entries

def group_by_age(entries, attr, buckets):
    now = datetime.now()
    grouped = {name: [] for name in buckets}

    for p, stat in entries:
        ts = datetime.fromtimestamp(getattr(stat, attr))
        age = now - ts
        placed = False
        for name, low, high in buckets:
            if (low is None or age >= timedelta(days=low)) and (high is None or age < timedelta(days=high)):
                grouped[name].append((p, ts, age))
                placed = True
                break
        if not placed:
            # fallback group
            grouped.setdefault('UNKNOWN', []).append((p, ts, age))
    return grouped

def list_recent(entries, attr, days):
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    recent = []
    for p, stat in entries:
        ts = datetime.fromtimestamp(getattr(stat, attr))
        if ts >= cutoff:
            recent.append((p, ts, now - ts))
    return recent

def print_grouped(grouped, title):
    print(f"\n=== {title} ===")
    for name, items in grouped.items():
        print(f"\n[{name}] ({len(items)} files)")
        for p, ts, age in sorted(items, key=lambda x: x[2], reverse=True)[:10]:  # show top 10
            print(f"{p} | date: {ts.strftime('%Y-%m-%d %H:%M:%S')} | age: {human_readable_delta(age)}")
        if len(items) > 10:
            print(f"... and {len(items) - 10} more ...")

def print_list(title, items):
    print(f"\n=== {title} ({len(items)} files) ===")
    for p, ts, age in sorted(items, key=lambda x: x[2], reverse=False):
        print(f"{p} | date: {ts.strftime('%Y-%m-%d %H:%M:%S')} | age: {human_readable_delta(age)}")


def main():
    parser = argparse.ArgumentParser(description="Analyze file age and access patterns.")
    parser.add_argument('path', nargs='?', default='.', help='Root directory to scan')
    parser.add_argument('--include-dirs', action='store_true', help='Include directories in analysis')
    parser.add_argument('--stale', type=int, help='List files not accessed in last N days')
    parser.add_argument('--recent', type=int, help='List files modified in last N days')
    parser.add_argument('--group', action='store_true', help='Group files by age buckets')
    args = parser.parse_args()

    entries = scan_files(args.path, include_dirs=args.include_dirs)

    if args.stale:
        stale = [e for e in entries if datetime.now() - datetime.fromtimestamp(e[1].st_atime) >= timedelta(days=args.stale)]
        stale_list = [(p, datetime.fromtimestamp(stat.st_atime), datetime.now() - datetime.fromtimestamp(stat.st_atime)) for p, stat in stale]
        print_list(f"Files not accessed in last {args.stale} days", stale_list)

    if args.recent:
        recent = list_recent(entries, 'st_mtime', args.recent)
        print_list(f"Files modified in last {args.recent} days", recent)

    if args.group:
        # Define buckets: (name, min_days, max_days)
        buckets = [
            ('>180 days', 180, None),
            ('90-180 days', 90, 180),
            ('30-90 days', 30, 90),
            ('7-30 days', 7, 30),
            ('<7 days', None, 7),
        ]
        grouped_mod = group_by_age(entries, 'st_mtime', buckets)
        print_grouped(grouped_mod, 'Modification Time Buckets')

        grouped_access = group_by_age(entries, 'st_atime', buckets)
        print_grouped(grouped_access, 'Access Time Buckets')

if __name__ == '__main__':
    main()
