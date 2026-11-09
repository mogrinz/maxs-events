"""Small isolated regression tests for event activity retention; no Flask server needed."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import sys

# Run in environment where Flask/icalendar are available (Pi venv).
from events import activity, history_read, read_history, prune_history, LOCK


def test_history_creation_and_purge():
    with TemporaryDirectory() as d:
        store=SimpleNamespace(root=Path(d))
        activity(store,{'username':'max'},'Assigned Screen 1')
        data=history_read(store)
        assert data['retention_days']==90
        assert data['entries'][0]['actor']=='max'
        assert data['entries'][0]['action']=='Assigned Screen 1'
        assert len(data['entries'])==1


def test_history_expiration():
    old=(datetime.now(timezone.utc)-timedelta(days=100)).isoformat()
    recent=datetime.now(timezone.utc).isoformat()
    d={'retention_days':90,'entries':[{'time':old},{'time':recent}]}
    assert len(prune_history(d)['entries'])==1
    d={'retention_days':'forever','entries':[{'time':old},{'time':recent}]}
    assert len(prune_history(d)['entries'])==2
