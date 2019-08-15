from unittest import TestCase

from canaryd.diff import Change
from canaryd.plugin import get_plugin_by_name, get_plugins


def setUpModule():
    get_plugins()


class TestServicesEvents(TestCase):
    def setUp(self):
        self.plugin = get_plugin_by_name('services')

    def test_should_apply_change_up_ports_only(self):
        change = Change(
            self.plugin, 'updated', 'key',
            data={'up_ports': [0, 1]},
        )

        should_apply = self.plugin.should_apply_change(change)
        self.assertEqual(should_apply, False)

    def test_should_apply_change(self):
        change = Change(
            self.plugin, 'updated', 'key',
            data={'up_ports': [0, 1], 'pid': [0, 1]},
        )

        should_apply = self.plugin.should_apply_change(change)
        self.assertEqual(should_apply, None)

    def test_action_for_change_not_update(self):
        change = Change(self.plugin, 'deleted', 'key')
        action = self.plugin.get_action_for_change(change)
        self.assertEqual(action, None)

    def test_action_for_change_restarted(self):
        change = Change(
            self.plugin, 'updated', 'key',
            data={'pid': [0, 1]},
        )

        action = self.plugin.get_action_for_change(change)
        self.assertEqual(action, 'restarted')

    def test_generate_resolved_issue(self):
        change = Change(self.plugin, 'deleted', 'key')

        issues = list(self.plugin.generate_issues_from_change(change, {}))

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0], ('resolved', None, None))


class TestMonitorEvents(TestCase):
    def setUp(self):
        self.plugin = get_plugin_by_name('monitor')

    def test_generate_resolved_issue(self):
        change = Change(self.plugin, 'deleted', 'key')

        issues = list(self.plugin.generate_issues_from_change(change, {}))

        self.assertEqual(len(issues), 1)
        self.assertEqual(
            issues[0],
            ('resolved', 'key is back to normal', None),
        )


class TestScriptEvents(TestCase):
    def setUp(self):
        self.plugin = get_plugin_by_name('scripts')

    def test_generate_resolved_issue(self):
        change = Change(self.plugin, 'deleted', 'key')

        issues = list(self.plugin.generate_issues_from_change(change, {}))

        self.assertEqual(len(issues), 1)
        self.assertEqual(
            issues[0],
            ('resolved', None, None),
        )
