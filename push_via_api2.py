#!/usr/bin/env python3
"""Push all files to GitHub repo via API."""
import json, base64, urllib.request, urllib.error, time, os, subprocess, sys

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
            print(f"  HTTP {e.code}: {body[:200]}", flush=True)
            if attempt < 2:
                time.sleep(2)
            else:
                raise
        except Exception as e:
            print(f"  Error: {e}", flush=True)
            if attempt < 2:
                time.sleep(2)
            else:
                raise

# Get file list
print("Getting file list...", flush=True)
files = subprocess.check_output(['git', 'ls-files']).decode().strip().split('\n')
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard']).decode().strip()
if untracked:
    extra = [f for f in untracked.split('\n') if f]
    files.extend(extra)

# Filter and normalize paths
valid_files = []
for f in files:
    if not f:
        continue
    f = f.replace('\\', '/')
    if os.path.isfile(f):
        valid_files.append(f)

print(f"Total files to upload: {len(valid_files)}", flush=True)

# Upload each file as a blob
tree_items = []
for i, fpath in enumerate(valid_files):
    if i % 50 == 0:
        print(f"  Uploading {i}/{len(valid_files)}...", flush=True)
    try:
        with open(fpath, 'rb') as fh:
            content = fh.read()
        if len(content) == 0:
            content = b' '
        blob_data = json.dumps({
            'content': base64.b64encode(content).decode(),
            'encoding': 'base64'
        }).encode()
        result = api_request(f'{API}/blobs', data=blob_data)
        if result and 'sha' in result:
            tree_items.append({
                'path': fpath,
                'mode': '100644',
                'type': 'blob',
                'sha': result['sha']
            })
        else:
            print(f"  WARNING: No sha for {fpath}", flush=True)
    except Exception as e:
        print(f"  ERROR uploading {fpath}: {e}", flush=True)
    if i > 0 and i % 30 == 0:
        time.sleep(0.3)

print(f"\nUploaded {len(tree_items)}/{len(valid_files)} blobs", flush=True)

# Create tree
print("Creating tree...", flush=True)
tree_data = json.dumps({'tree': tree_items}).encode()
result = api_request(f'{API}/trees', data=tree_data)
tree_sha = result['sha']
print(f"  Tree SHA: {tree_sha}", flush=True)

# Create commit (with parent = initial commit)
print("Creating commit...", flush=True)
# Get current main HEAD
try:
    head_result = api_request(f'{API}/refs/heads/main')
    parent_sha = head_result['object']['sha']
    parents = [parent_sha]
except:
    parents = []

commit_data = json.dumps({
    'message': 'Official v6.4.2 + Accessibility Service + HideToolbar',
    'tree': tree_sha,
    'parents': parents
}).encode()
result = api_request(f'{API}/commits', data=commit_data)
commit_sha = result['sha']
print(f"  Commit SHA: {commit_sha}", flush=True)

# Update main branch ref
print("Updating main branch...", flush=True)
ref_data = json.dumps({'sha': commit_sha, 'force': True}).encode()
result = api_request(f'{API}/refs/heads/main', data=ref_data, method='PATCH')
print(f"  Ref updated: {result.get('ref', 'unknown')}", flush=True)

print(f"\nPush complete! {len(tree_items)} files uploaded.", flush=True)
print(f"Actions: https://github.com/{REPO}/actions", flush=True)
