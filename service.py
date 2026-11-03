# The service's scheduler, the main process of the app's container (the
# image's CMD, Dockerfile): it runs main.py's jobs below, each every so many
# minutes, one run at a time and each in a process of its own, so one run's
# state never carries into the next. When more than one is due, the one due
# longest runs first; a run that takes longer than its interval only makes the
# next one late. The scores are published weekly, after the run going at the
# time. Times are UTC. Each run's output goes to the app's log.
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
# The weekly publish, on Mondays from 08:30.
PUBLISH = ['--scan', '0', '--crawl', '0', '--publish']
PUBLISH_DAY, PUBLISH_TIME = 0, datetime.time(8, 30)


def next_job(next_at: list, now: float) -> int | None:
    # The job to run now, given when each is due (next_at): the one due
    # longest, or None while none is.
    i = min(range(len(JOBS)), key=next_at.__getitem__)
    return i if next_at[i] <= now else None


def publish_slot(now: datetime.datetime) -> datetime.datetime:
    # The latest publish time at or before now.
    slot = datetime.datetime.combine(now.date(), PUBLISH_TIME, now.tzinfo)
    slot -= datetime.timedelta(days=(now.weekday() - PUBLISH_DAY) % 7)
    if slot > now:
        slot -= datetime.timedelta(days=7)
    return slot


def run(args: list) -> None:
    subprocess.run([sys.executable, '-u', str(MAIN), *args], check=False)


def main():
    print("Scheduler started; times are UTC.", flush=True)
    next_at = [0.0] * len(JOBS)
    # The next publish is the next slot's, not one on starting.
    published = publish_slot(datetime.datetime.now(datetime.UTC))
    while True:
        slot = publish_slot(datetime.datetime.now(datetime.UTC))
        if slot > published:
            published = slot
            run(PUBLISH)
        i = next_job(next_at, time.time())
        if i is None:
            # Until the next job is due, checking the publish each minute.
            time.sleep(max(1.0, min(min(next_at) - time.time(), 60.0)))
            continue
        next_at[i] = time.time() + JOBS[i][0] * 60
        run(JOBS[i][1])


if __name__ == '__main__':
    main()
