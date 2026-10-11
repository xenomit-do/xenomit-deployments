#!/usr/bin/env python3
"""Promote a signed image digest into the deployments repository.

Invoked by .github/workflows/promote-image.yml via workflow_dispatch.
Validates the inputs strictly, updates only the
digest field for the mapped file, pushes an automation branch, and opens a PR
using a narrowly scoped GitHub App token. No-op digests exit cleanly without a PR.
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

# image name -> (required source_repository, file to update, updater kind)
IMAGE_MAP = {
    "orchestrator": ("xenomit-do/xenomit-orchestrator",
                     "apps/control-plane/kustomization.yaml", "kustomize"),
    "web-panel": ("xenomit-do/xenomit-web-panel",
                  "apps/panel/kustomization.yaml", "kustomize"),
    "botd": ("xenomit-do/xenomit-botd", "fleet/botd-image.json", "botd-json"),
}

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["APP_TOKEN"]
RUN_ID = os.environ.get("RUN_ID", "manual")


def fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def api(method, path, body=None, ok=(200, 201), missing_ok=False):
    req = urllib.request.Request(
        f"{API}/repos/{REPO}{path}",
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status not in ok:
                fail(f"{method} {path} -> {resp.status}")
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        if missing_ok and e.code == 404:
            return None
        detail = e.read().decode(errors="replace")[:500]
        fail(f"{method} {path} -> {e.code}: {detail}")


def update_kustomize(text, digest):
    new, n = re.subn(r"(digest:\s*)sha256:[0-9a-f]{64}", rf"\g<1>{digest}",
                     text, count=1)
    if n == 0:
        fail("no digest field found in kustomization")
    return new


def update_botd_json(text, digest, source_sha):
    doc = json.loads(text) if text.strip() else {}
    # Preserve the existing fleet record contract consumed by operators and
    # runbooks: this is an image reference, not a bare digest field.
    doc["image"] = f"ghcr.io/xenomit-do/xenomit-botd@{digest}"
    doc["sourceSha"] = source_sha
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def main():
    image = os.environ.get("PAYLOAD_IMAGE", "")
    digest = os.environ.get("PAYLOAD_DIGEST", "")
    source_repo = os.environ.get("PAYLOAD_SOURCE_REPOSITORY", "")
    source_sha = os.environ.get("PAYLOAD_SOURCE_SHA", "")

    if image not in IMAGE_MAP:
        fail(f"image {image!r} not in allowlist {sorted(IMAGE_MAP)}")
    expected_repo, path, kind = IMAGE_MAP[image]
    if source_repo != expected_repo:
        fail(f"source_repository {source_repo!r} != {expected_repo!r}")
    if not DIGEST_RE.match(digest):
        fail(f"invalid digest {digest!r}")
    if not SHA_RE.match(source_sha):
        fail(f"invalid source_sha {source_sha!r}")

    main_sha = api("GET", "/git/ref/heads/main")["object"]["sha"]
    branch = f"automation/promote-{image}-{digest.removeprefix('sha256:')[:12]}"

    existing = api("GET", f"/contents/{path}?ref=main", missing_ok=True)
    old_text = base64.b64decode(existing["content"]).decode() if existing else ""

    if kind == "botd-json":
        new_text = update_botd_json(old_text, digest, source_sha)
    else:
        new_text = update_kustomize(old_text, digest)
    if new_text == old_text:
        print(f"{path} already at {digest}; nothing to do")
        return

    if not api("GET", f"/git/ref/heads/{branch}", missing_ok=True):
        api("POST", "/git/refs",
            {"ref": f"refs/heads/{branch}", "sha": main_sha}, ok=(201,))

    on_branch = api("GET", f"/contents/{path}?ref={branch}", missing_ok=True)
    put = {
        "message": f"promote {image} to {digest} (from {source_repo}@{source_sha[:12]})",
        "content": base64.b64encode(new_text.encode()).decode(),
        "branch": branch,
    }
    if on_branch:
        put["sha"] = on_branch["sha"]
    api("PUT", f"/contents/{path}", put)

    head = f"{REPO.split('/')[0]}:{branch}"
    prs = api("GET", f"/pulls?head={head}&state=open")
    if prs:
        print(f"PR already open: {prs[0]['html_url']}")
        return
    pr = api("POST", "/pulls", {
        "title": f"promote {image} to {digest[:19]}",
        "head": branch,
        "base": "main",
        "body": (f"Promoted by workflow_dispatch `promote-image` "
                 f"(run {RUN_ID}).\n\n"
                 f"- image: `{image}`\n- digest: `{digest}`\n"
                 f"- source: `{source_repo}@{source_sha}`"),
    })
    print(f"created PR: {pr['html_url']}")


if __name__ == "__main__":
    main()
