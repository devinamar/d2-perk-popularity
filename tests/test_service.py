# The scheduler's choices (service.py): which job runs next, and when the
# timed jobs (the daily purge, the weekly publish) are due. Times are UTC.
import datetime

import service


def at(day, hour, minute):
    return datetime.datetime(2026, 10, day, hour, minute, tzinfo=datetime.UTC)


def test_a_job_runs_once_due(monkeypatch):
    monkeypatch.setattr(service, 'JOBS', [(5, ['a']), (15, ['b'])])
    # next_at: when each job is due; the one due longest runs first.
    assert service.next_job([100.0, 50.0], now=60.0) == 1
    assert service.next_job([10.0, 50.0], now=60.0) == 0
    assert service.next_job([0.0, 0.0], now=0.0) == 0  # on starting, the first
    assert service.next_job([100.0, 90.0], now=60.0) is None


def test_a_timed_job_falls_due_at_its_latest_slot():
    # 2026-10-26 is a Monday. The weekly publish, Mondays at 08:30:
    publish = (0, datetime.time(8, 30))
    assert service.slot(at(26, 8, 30), *publish) == at(26, 8, 30)
    assert service.slot(at(26, 8, 29), *publish) == at(19, 8, 30)
    assert service.slot(at(27, 1, 0), *publish) == at(26, 8, 30)
    assert service.slot(at(25, 23, 0), *publish) == at(19, 8, 30)
    # The daily purge, at 08:00:
    purge = (None, datetime.time(8, 0))
    assert service.slot(at(27, 8, 0), *purge) == at(27, 8, 0)
    assert service.slot(at(27, 7, 59), *purge) == at(26, 8, 0)
    assert service.slot(at(27, 23, 0), *purge) == at(27, 8, 0)
    # On a Monday the purge falls due before the publish, and runs first.
    assert [args[-1] for _, _, args in service.TIMED] == ['--purge', '--publish']
