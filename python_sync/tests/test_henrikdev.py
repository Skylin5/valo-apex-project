"""Tests du client HenrikDev (sans réseau : requests.get est simulé)."""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import henrikdev
except ImportError:  # requests absent de l'environnement local
    henrikdev = None


def response(status=200, data=None, headers=None):
    resp = mock.Mock()
    resp.status_code = status
    resp.headers = headers or {}
    resp.json.return_value = {"status": status, "data": data}
    return resp


@unittest.skipIf(henrikdev is None, "requests non installé")
class HenrikClientTest(unittest.TestCase):
    def setUp(self):
        henrikdev._cache.clear()
        patches = [
            mock.patch.object(henrikdev, "HENRIKDEV_API_KEY", "HDEV-test"),
            mock.patch.object(henrikdev.time, "sleep"),
        ]
        self.sleep = patches[1].start()
        patches[0].start()
        self.addCleanup(mock.patch.stopall)

    def test_missing_key_raises_503_without_network_call(self):
        with mock.patch.object(henrikdev, "HENRIKDEV_API_KEY", ""), \
                mock.patch.object(henrikdev.requests, "get") as get:
            with self.assertRaises(henrikdev.HenrikError) as ctx:
                henrikdev.fetch_matches("eu", "Nova", "roma")
        self.assertEqual(ctx.exception.status, 503)
        get.assert_not_called()

    def test_matches_url_params_and_size_cap(self):
        with mock.patch.object(henrikdev.requests, "get", return_value=response(data=[{"a": 1}])) as get:
            result = henrikdev.fetch_matches("eu", "No va", "roma", size=50, mode="competitive")
        self.assertEqual(result, [{"a": 1}])
        url = get.call_args.args[0]
        self.assertTrue(url.endswith("/v4/matches/eu/pc/No%20va/roma"))
        self.assertEqual(get.call_args.kwargs["params"], {"size": 10, "mode": "competitive"})

    def test_404_is_account_not_found(self):
        with mock.patch.object(henrikdev.requests, "get", return_value=response(404)):
            with self.assertRaises(henrikdev.HenrikError) as ctx:
                henrikdev.fetch_matches("eu", "X", "1")
        self.assertEqual(ctx.exception.status, 404)

    def test_429_is_retried_then_succeeds(self):
        replies = [response(429, headers={"Retry-After": "2"}), response(data=[1])]
        with mock.patch.object(henrikdev.requests, "get", side_effect=replies) as get:
            self.assertEqual(henrikdev.fetch_matches("eu", "X", "1"), [1])
        self.assertEqual(get.call_count, 2)
        self.sleep.assert_called_with(2.0)

    def test_429_persistent_raises(self):
        with mock.patch.object(henrikdev.requests, "get", return_value=response(429)) as get:
            with self.assertRaises(henrikdev.HenrikError) as ctx:
                henrikdev.fetch_matches("eu", "X", "1")
        self.assertEqual(ctx.exception.status, 429)
        self.assertEqual(get.call_count, henrikdev.MAX_RETRIES_ON_429 + 1)

    def test_second_identical_call_uses_cache(self):
        with mock.patch.object(henrikdev.requests, "get", return_value=response(data=[1])) as get:
            henrikdev.fetch_matches("eu", "X", "1")
            henrikdev.fetch_matches("eu", "X", "1")
        self.assertEqual(get.call_count, 1)

    def test_mmr_history_reads_history_key(self):
        data = {"account": {}, "history": [{"match_id": "m1"}]}
        with mock.patch.object(henrikdev.requests, "get", return_value=response(data=data)):
            self.assertEqual(henrikdev.fetch_mmr_history("eu", "X", "1"), [{"match_id": "m1"}])


if __name__ == "__main__":
    unittest.main()
