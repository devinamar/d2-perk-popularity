# The API client's replies: the Response, Bungie errors, and the retries for
# throttles and server errors, against a stand-in session.
import pytest
import requests

from sources.bungie import api as bungie_api


class Reply:
    # An HTTP reply: a status and a JSON body (None for one that isn't JSON).
    def __init__(self, status, body):
        self.status_code, self.body = status, body

    def json(self):
        if self.body is None:
            raise ValueError('not JSON')
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(self.status_code)


def client(monkeypatch, *replies):
    # A BungieAPI whose session answers with replies in turn, without waiting.
    monkeypatch.setattr(bungie_api.time, 'sleep', lambda _: None)
    api = bungie_api.BungieAPI('key')
    queue = list(replies)
    monkeypatch.setattr(api.session, 'request', lambda *_, **__: queue.pop(0))
    return api, queue


def test_returns_the_response(monkeypatch):
    api, _ = client(monkeypatch, Reply(200, {'ErrorCode': 1, 'Response': {'a': 1}}))
    assert api.get_pgcr(1) == {'a': 1}


def test_raises_bungie_errors(monkeypatch):
    api, _ = client(monkeypatch, Reply(200, {'ErrorCode': 1653, 'Message': 'Not found'}))
    with pytest.raises(bungie_api.BungieError) as e:
        api.get_pgcr(1)
    assert e.value.code == 1653


def test_retries_throttles_and_server_errors(monkeypatch):
    api, queue = client(
        monkeypatch,
        Reply(200, {'ErrorCode': 36, 'ThrottleSeconds': 1}),
        Reply(503, None),
        Reply(200, {'ErrorCode': 1, 'Response': 'ok'}),
    )
    assert api.get_pgcr(1) == 'ok'
    assert queue == []


def test_a_server_error_that_lasts_raises(monkeypatch):
    api, _ = client(monkeypatch, *[Reply(502, None)] * (bungie_api.RETRIES + 1))
    with pytest.raises(requests.HTTPError):
        api.get_pgcr(1)


def test_a_page_without_an_error_code_is_a_bungie_error(monkeypatch):
    api, _ = client(monkeypatch, Reply(404, None))
    with pytest.raises(bungie_api.BungieError) as e:
        api.get_pgcr(1)
    assert e.value.code == 0
