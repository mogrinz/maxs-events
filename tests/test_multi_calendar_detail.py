"""Regression tests for multi-calendar migration and Detail View event selection."""
from datetime import datetime
from events import normalize_screen, detail_selection


def test_legacy_screen_migrates_without_losing_calendar():
    old = {'source_id': 'calendar-old', 'title': 'Check In'}
    updated = normalize_screen(old)
    assert updated['source_ids'] == ['calendar-old']
    assert updated['view'] == 'list'
    assert updated['color_code'] is False
    assert old['source_id'] == 'calendar-old'


def test_overlapping_event_remains_featured_until_end():
    a={'start':'2026-11-03T10:00:00-05:00','end':'2026-11-03T11:00:00-05:00','title':'Lecture A','all_day':False}
    b={'start':'2026-11-03T10:45:00-05:00','end':'2026-11-03T11:30:00-05:00','title':'Lecture B','all_day':False}
    featured,later=detail_selection([a,b],datetime.fromisoformat('2026-11-03T10:50:00-05:00'))
    assert featured is a and later is b
    featured,later=detail_selection([a,b],datetime.fromisoformat('2026-11-03T11:00:00-05:00'))
    assert featured is b and later is None


def test_detail_all_day_not_preferred_over_timed():
    all_day={'start':'2026-11-03T00:00:00-05:00','end':'2026-11-04T00:00:00-05:00','title':'Expo','all_day':True}
    timed={'start':'2026-11-03T10:00:00-05:00','end':'2026-11-03T11:00:00-05:00','title':'Talk','all_day':False}
    featured,_=detail_selection([all_day,timed],datetime.fromisoformat('2026-11-03T09:00:00-05:00'),True)
    assert featured is timed
