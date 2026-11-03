# The scheduler's choices (service.py): which job runs next, and when the
# weekly publish is due. Times are UTC.
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


def test_the_publish_slot_is_the_latest_monday_0830():
    # 2026-10-26 is a Monday.
    assert service.publish_slot(at(26, 8, 30)) == at(26, 8, 30)
    assert service.publish_slot(at(26, 8, 29)) == at(19, 8, 30)
    assert service.publish_slot(at(27, 1, 0)) == at(26, 8, 30)
    assert service.publish_slot(at(25, 23, 0)) == at(19, 8, 30)
