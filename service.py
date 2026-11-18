# The service's scheduler, the main process of the app's container (the
# image's CMD, Dockerfile): it runs main.py's jobs below, each every so many
# minutes, one run at a time and each in a process of its own, so one run's
# state never carries into the next. When more than one is due, the one due
# longest runs first; a run that takes longer than its interval only makes the
# next one late. The timed jobs (the daily purge, the weekly publish) run after
# the run going at their time. Times are UTC. Each run's output goes to the
# app's log.
import datetime
import pathlib
import subprocess
import sys
import time

MAIN = pathlib.Path(__file__).with_name('main.py')

# (every this many minutes, main.py's arguments)
JOBS = [
    # The newest carnage reports, read minutes after their matches, while the
    # players likely still have the weapons they used equipped: every hard one
    # kept, normal ones sampled (67 per category a run, about 200 every 15
    # minutes).
    # Each run also reads again 3000 of the raid and dungeon PGCRs stored before
    # the scan read how their run started, until none is left.
    (5, ['--scan', '3000', '--crawl', '0', '--per-category', '67', '--catch-up', '3000']),
]
# (weekday from Monday 0, or None for every day; time; main.py's arguments),
# in the order they run when both are due.
TIMED = [
    # The purge, daily from 08:00: rolling the votes to the window and dropping
    # the copies, plugs and raw PGCRs nothing needs any more takes minutes on
    # the whole database and changes little in a day, so runs don't do it.
    (None, datetime.time(8, 0), ['--scan', '0', '--crawl', '0', '--purge']),
    # The publish, on Mondays from 08:30, after that day's purge.
    (0, datetime.time(8, 30), ['--scan', '0', '--crawl', '0', '--publish']),
]


def next_job(next_at: list, now: float) -> int | None:
    # The job to run now, given when each is due (next_at): the one due
    # longest, or None while none is.
    i = min(range(len(JOBS)), key=next_at.__getitem__)
    return i if next_at[i] <= now else None


def slot(now: datetime.datetime, weekday: int | None, at: datetime.time) -> datetime.datetime:
    # The latest time at or before now a job timed at weekday (None: every day)
    # and at falls due.
    due = datetime.datetime.combine(now.date(), at, now.tzinfo)
    if weekday is not None:
        due -= datetime.timedelta(days=(now.weekday() - weekday) % 7)
    if due > now:
        due -= datetime.timedelta(days=1 if weekday is None else 7)
    return due


def run(args: list) -> None:
    subprocess.run([sys.executable, '-u', str(MAIN), *args], check=False)


def main():
    print("Scheduler started; times are UTC.", flush=True)
    next_at = [0.0] * len(JOBS)
    # Each timed job next runs at its next slot, not on starting.
    now = datetime.datetime.now(datetime.UTC)
    done = [slot(now, weekday, at) for weekday, at, _ in TIMED]
    while True:
        now = datetime.datetime.now(datetime.UTC)
        for k, (weekday, at, args) in enumerate(TIMED):
            due = slot(now, weekday, at)
            if due > done[k]:
                done[k] = due
                run(args)
        i = next_job(next_at, time.time())
        if i is None:
            # Until the next job is due, checking the timed ones each minute.
            time.sleep(max(1.0, min(min(next_at) - time.time(), 60.0)))
            continue
        next_at[i] = time.time() + JOBS[i][0] * 60
        run(JOBS[i][1])


if __name__ == '__main__':
    main()
