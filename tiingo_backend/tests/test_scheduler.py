import pytest

pytest.importorskip("apscheduler")

from features.scheduler.scheduler import get_scheduler, list_jobs


def test_scheduler_singleton():
    s1 = get_scheduler()
    s2 = get_scheduler()
    assert s1 is s2


def test_list_jobs_not_running():
    jobs = list_jobs()
    assert isinstance(jobs, list)
