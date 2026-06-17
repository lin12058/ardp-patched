#!/usr/bin/env python3
"""Push all files to GitHub repo via API (bypassing git push network issues)."""
import json, base64, urllib.request, urllib.error, time, subprocess, os, sys

TOKEN = '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'
REPO = 'lin12058/ardp-patched'
API = f'https://api.github.com/repos/{REPO}/git'
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Accept': 'application/vnd.github+json',
    'Content-Type': 'application/json',
    'User-Agent': 'lin12058'
}

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def api_request(url, data=None, method=None):
    """Make a GitHub API request with retries."""
    for attempt in range(3):
        try:
            if data is not None:
                req = urllib.request.Request(url, data=data, headers=HEADERS)
            else:
                req = urllib.request.Request(url, headers=HEADERS)
            if method:
                req.get_method = lambda: method
            resp = urllib.request.urlopen(req, timeout=60)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            print(f"  HTTP {e.code}: {body[:200]}")
            if attempt < 2:
                time.sleep(2)
            else:
                raise
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < 2:
                time.sleep(2)
            else:
                raise

# Get list of files from git
print("Getting file list from git...")
files = subprocess.check_output(['git', 'ls-files']).decode().strip().split('\n')
# Also add untracked files that aren't in git
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard']).decode().strip()
if untracked:
    files.extend([f for f in untracked.split('\n') if f])

print(f"Total files to upload: {len(files)}")

# Upload each file as a blob
tree_items = []
for i, fpath in enumerate(files):
    if not fpath or not os.path.isfile(fpath):
        continue
    if i % 50 == 0:
        print(f"  Uploading {i}/{len(files)}...")

    try:
        with open(fpath, 'rb') as fh:
            content = fh.read()

        # Skip empty files
        if len(content) == 0:
            content = b' '

        blob_data = json.dumps({
            'content': base64.b64encode(content).decode(),
            'encoding': 'base64'
        }).encode()

        result = api_request(f'{API}/blobs', data=blob_data)
        if result and 'sha' in result:
            tree_items.append({
                'path': fpath.replace('\\', '/'),
                'mode': '100644',
                'type': 'blob',
                'sha': result['sha']
            })
        else:
            print(f"  WARNING: No sha for {fpath}")
    except Exception as e:
        print(f"  ERROR uploading {fpath}: {e}")

    # Rate limit: sleep every 30 files
    if i > 0 and i % 30 == 0:
        time.sleep(0.5)

print(f"\nUploaded {len(tree_items)}/{len(files)} files as blobs")

# Create tree
print("Creating tree...")
tree_data = json.dumps({'tree': tree_items}).encode()
result = api_request(f'{API}/trees', data=tree_data)
tree_sha = result['sha']
print(f"  Tree SHA: {tree_sha}")

# Create commit
print("Creating commit...")
commit_data = json.dumps({
    'message': 'Official v6.4.2 + Accessibility Service + HideToolbar',
    'tree': tree_sha,
    'parents': []
}).encode()
result = api_request(f'{API}/commits', data=commit_data)
commit_sha = result['sha']
print(f"  Commit SHA: {commit_sha}")

# Update main branch ref
print("Updating main branch...")
ref_data = json.dumps({'sha': commit_sha}).encode()
result = api_request(f'{API}/refs/heads/main', data=ref_data, method='POST')
print(f"  Ref updated: {result.get('ref', 'unknown')}")

print("\nPush complete! Check Actions at:")
print(f"  https://github.com/{REPO}/actions")
