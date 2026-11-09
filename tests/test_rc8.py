"""RC8 regression checks; run on desktop without Pi or Flask dependencies."""
from pathlib import Path
import sys
import tempfile
from datetime import datetime
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from network_service import Controller
from test_network import FakeNM, HOME, AP

OTHER = '33333333-3333-3333-3333-333333333333'


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.nm = FakeNM()
        self.nm.current = OTHER
        self.nm.profiles = lambda: [
            {'uuid': HOME, 'name': 'old wifi', 'mode': 'infrastructure'},
            {'uuid': OTHER, 'name': 'TestNetwork', 'mode': 'infrastructure'},
            {'uuid': AP, 'name': 'hotspot', 'mode': 'ap'},
        ]
        self.controller = Controller(self.nm, Path(self.temp.name)/'state.json', lambda: 1000, lambda callback: None)
        self.controller.state = {'confirmed': HOME, 'internet': HOME, 'hotspot': AP,
                                 'message': 'Saved network unavailable. Retrying automatically.'}
        self.controller.save()

    def tearDown(self):
        self.temp.cleanup()

    def test_active_wifi_not_disconnected_by_startup_or_retry(self):
        self.controller.recover_startup()
        self.controller.tick()
        self.assertEqual(self.nm.current, OTHER)
        self.assertTrue(self.controller.status()['can_adopt'])
        self.assertIn('differs', self.controller.status()['message'])

    def test_adopt_current_profile_without_activating(self):
        self.controller.recover_startup()
        result = self.controller.dispatch({'action':'adopt_internet', 'profile':OTHER})
        self.assertIn('No network switch', result['message'])
        self.assertEqual(self.controller.state['confirmed'], OTHER)
        self.assertEqual(self.controller.state['internet'], OTHER)
        self.assertEqual(self.nm.current, OTHER)
        self.assertIn((OTHER, True), self.nm.preferences)
        self.assertIn((HOME, False), self.nm.preferences)
        self.assertFalse(self.controller.status()['can_adopt'])
        self.assertNotIn('unavailable', self.controller.status()['message'])
        # Controller restart must keep the adopted preference.
        restarted = Controller(self.nm, self.controller.path, lambda: 1000, lambda callback: None)
        restarted.recover_startup()
        self.assertEqual(self.nm.current, OTHER)

    def test_wrong_profile_or_pending_trial_rejected(self):
        for profile in (HOME, AP, 'arbitrary'):
            with self.assertRaises(ValueError):
                self.controller.dispatch({'action':'adopt_internet', 'profile':profile})
        self.controller.state['pending']={'id':'trial','prior':HOME,'target':AP,'mode':'hotspot','deadline':2000}
        with self.assertRaises(ValueError):
            self.controller.dispatch({'action':'adopt_internet', 'profile':OTHER})

    def test_cannot_adopt_hotspot(self):
        self.nm.current = AP
        self.assertFalse(self.controller.status()['can_adopt'])
        with self.assertRaises(ValueError):
            self.controller.dispatch({'action':'adopt_internet', 'profile':AP})

    def test_stale_saved_profile_missing_still_preserves_active_wifi(self):
        self.controller.state['confirmed']='44444444-4444-4444-4444-444444444444'
        self.controller.recover_startup()
        self.controller.tick()
        self.assertEqual(self.nm.current, OTHER)

    def test_confirmed_hotspot_restore_not_changed(self):
        self.controller.state['confirmed']=AP
        self.controller.recover_startup()
        self.assertEqual(self.nm.current, AP)


def test_theme_and_date_controls():
    js = (ROOT/'static/events-admin.js').read_text()
    assert "if($('date_mode').value==='today')$('custom_date').value=''" in js
    assert "date_mode:$('date_mode').value,custom_date:$('date_mode').value==='today'?'':" in js
    assert "body['custom_date']=''" in (ROOT/'events.py').read_text()
    assert "new Option('--- Custom ---','custom')" in (ROOT/'static/events-themes.js').read_text()


def test_success_message_timers_are_independent_and_errors_persist():
    js = (ROOT/'static/events-sources.js').read_text()
    assert 'const feedbackTimers=new Map()' in js
    assert 'clearTimeout(feedbackTimers.get(id))' in js
    assert '},3000)' in js
    assert 'if(!error)' in js


def test_demo_ics_daily_recurring():
    from dateutil.rrule import rrulestr
    for room in 'abcd':
        data = (ROOT/'examples'/f'demo-room-{room}.ics').read_text()
        assert data.count('BEGIN:VEVENT') == 4
        assert data.count('RRULE:FREQ=DAILY') == 4
        assert data.count('DTSTART:20261101T') == 4
        starts = [line.removeprefix('DTSTART:') for line in data.splitlines() if line.startswith('DTSTART:')]
        for start in starts:
            rule=rrulestr('FREQ=DAILY',dtstart=datetime.strptime(start,'%Y%m%dT%H%M%S'))
            assert rule[4].date().isoformat() == '2026-11-05'


def test_legacy_controller_migration_is_separate_from_general_upgrade():
    script = (ROOT/'upgrade.sh').read_text()
    helper = (ROOT/'legacy_network_controller_migration.py').read_text()
    assert 'legacy_network_controller_migration.py' not in script
    assert 'install_network_service.py' not in script
    assert "json.loads(STATE.read_text()).get('pending')" in helper
    assert "['systemctl', 'restart', SERVICE]" in helper
    assert "os.replace(name, INSTALLED)" in helper
