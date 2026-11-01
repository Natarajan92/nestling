from scripts.capture_screenshots import safe_request


def test_only_local_read_routes_and_deterministic_today_are_safe():
    assert safe_request('GET', 'http://127.0.0.1:8010/api/lessons/burping')
    assert safe_request('POST', 'http://127.0.0.1:8010/api/today')
    for path in ('/api/ask', '/api/capture/search', '/api/capture/estimate', '/api/voice/speak', '/api/policy/ask'):
        assert not safe_request('POST', 'http://127.0.0.1:8010' + path)
