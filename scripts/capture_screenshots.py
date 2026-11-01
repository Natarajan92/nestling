"""Capture a synthetic local demo profile, never a personal browser profile.

Optional tool dependency: uv run --with playwright python scripts/capture_screenshots.py
Add --allow-rule-ask for the single fixed, code-owned emergency example (zero LLM calls).
General Ask, voice, policy and Capture provider routes remain blocked.
This utility is not run automatically during builds or submission packaging.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

REDFLAG = 'I am 32 weeks pregnant and have a severe headache with blurred vision'
PROFILE = {'due_date': '2027-02-08', 'birth_date': None, 'tradition': 'tamil_nadu',
           'diet': 'veg', 'city': 'Bengaluru', 'insurer': None, 'parent_role': 'mother',
           'consent': {'store_profile': True, 'save_journal': False, 'voice': False}}


def safe_request(method, url):
    path = urlsplit(url).path
    if method in ('GET', 'HEAD'):
        return (path in ('/api/health', '/api/sources', '/api/checklist', '/api/lessons')
                or path.startswith('/api/lessons/') or path.startswith('/media/lessons/'))
    return method == 'POST' and path == '/api/today'


def capture(args):
    from playwright.sync_api import sync_playwright
    if args.allow_rule_ask:
        from nestling import guardian
        if not guardian.decide(REDFLAG).escalate:
            raise RuntimeError('The demo must be a code-owned emergency before allowing a request')
    args.output.mkdir(parents=True, exist_ok=True)
    blocked, ask_count = [], 0
    allowed_host = urlsplit(args.api).netloc
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(viewport={'width': 390, 'height': 844},
                                      device_scale_factor=1, timezone_id='Asia/Kolkata')
        context.add_init_script('localStorage.setItem("nestling:profile", ' + json.dumps(json.dumps(PROFILE)) + ');')

        def guard(route):
            nonlocal ask_count
            request = route.request
            url = urlsplit(request.url)
            if not (url.path.startswith('/api/') or url.path.startswith('/media/')):
                route.continue_()
                return
            permitted = url.netloc == allowed_host and safe_request(request.method, request.url)
            if (args.allow_rule_ask and ask_count == 0 and url.netloc == allowed_host
                    and request.method == 'POST' and url.path == '/api/ask'):
                payload = request.post_data_json or {}
                permitted = payload.get('message') == REDFLAG
                if permitted:
                    ask_count += 1
            if permitted:
                route.continue_()
            else:
                blocked.append({'method': request.method, 'path': url.path})
                route.abort('blockedbyclient')

        context.route('**/*', guard)
        page = context.new_page()
        for name, path in [('today', '/'), ('lesson', '/lessons/burping'), ('capture', '/celebrate/capture')]:
            page.goto(args.web.rstrip('/') + path, wait_until='networkidle')
            page.get_by_role('main').wait_for()
            page.evaluate('document.fonts.ready')
            if page.get_by_text('This page couldn’t load', exact=False).count():
                raise RuntimeError(f'{path} failed; no screenshot is accepted')
            page.screenshot(path=str(args.output / f'{name}.png'), full_page=True)
        if args.allow_rule_ask:
            page.goto(args.web.rstrip('/') + '/ask', wait_until='networkidle')
            page.get_by_role('textbox', name='Your question').fill(REDFLAG)
            page.get_by_role('button', name='Send', exact=True).click()
            page.get_by_text('Please contact your doctor or go to the hospital now.', exact=False).wait_for()
            page.screenshot(path=str(args.output / 'ask_redflag.png'), full_page=True)
        browser.close()
    if blocked:
        raise RuntimeError('Unexpected API requests blocked: ' + json.dumps(blocked))
    print(json.dumps({'synthetic_profile': True, 'viewport': '390x844', 'general_paid_routes_allowed': False,
                      'code_owned_ask_count': ask_count, 'output': str(args.output)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--web', default='http://localhost:3000')
    parser.add_argument('--api', default='http://127.0.0.1:8010')
    parser.add_argument('--output', type=Path, default=Path('docs/media'))
    parser.add_argument('--allow-rule-ask', action='store_true')
    capture(parser.parse_args())
