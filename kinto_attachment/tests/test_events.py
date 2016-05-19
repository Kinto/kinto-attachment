from kinto.tests.core.support import unittest

from . import BaseWebTest


class Listener(object):
    def __init__(self):
        self.received = []

    def __call__(self, event):
        self.received.append(event)


listener = Listener()


def load_from_config(config, prefix):
    return listener


class ResourceChangedTest(BaseWebTest, unittest.TestCase):
    config = 'config/events.ini'

    def test_resource_changed_is_triggered_when_attachment_is_set(self):
        before = len(listener.received)
        self.upload()
        self.assertEqual(len(listener.received), before + 1)

    def test_action_is_create_or_update(self):
        self.upload()
        self.assertEqual(listener.received[-1].payload['action'], 'create')
        self.upload()
        self.assertEqual(listener.received[-1].payload['action'], 'update')

    def test_payload_attribute_are_sound(self):
        self.upload()
        payload = listener.received[-1].payload
        self.assertEqual(payload['uri'], self.endpoint_uri)
        self.assertEqual(payload['resource_name'], 'record')
        self.assertEqual(payload['record_id'], self.record_id)
        self.assertEqual(payload['collection_id'], 'fonts')
        self.assertEqual(payload['bucket_id'], 'fennec')
