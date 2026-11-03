# Minimal client for GitHub's repository contents API: publishes one file to a
# branch, one commit per publish. The token is a fine-grained personal access
# token with Contents read and write on that one repository.
import base64

import requests

API_URL = 'https://api.github.com'


def put_file(token, repo, branch, path, content: bytes, message, session=None) -> str:
    # Create or replace path on branch of repo ('owner/name') with content,
    # committing it with message. Returns the commit's URL; raises on an HTTP
    # error. The current file is looked up with the object media type, which
    # gives its sha for files over 1 MB too.
    session = session or requests.Session()
    headers = {'Authorization': f'Bearer {token}', 'X-GitHub-Api-Version': '2022-11-28'}
    url = f'{API_URL}/repos/{repo}/contents/{path}'
    current = session.get(
        url,
        params={'ref': branch},
        headers={**headers, 'Accept': 'application/vnd.github.object'},
        timeout=30,
    )
    if current.status_code != 404:
        current.raise_for_status()
    body = {
        'message': message,
        'content': base64.b64encode(content).decode('ascii'),
        'branch': branch,
    }
    if current.status_code == 200:
        body['sha'] = current.json()['sha']
    reply = session.put(
        url, json=body, headers={**headers, 'Accept': 'application/vnd.github+json'}, timeout=120
    )
    reply.raise_for_status()
    return reply.json()['commit']['html_url']
