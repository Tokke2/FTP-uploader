# Copyright (c) 2026 Rickard Längkvist
"""Optional Ed25519 trust pin. No auto-trust, embedded secret or pretend signing."""
import base64
import hashlib
import json
from app_paths import config_dir


def verify_archive(archive, release, fetch):
    trust_file = config_dir()/'release-trust.json'
    if not trust_file.exists(): return 'unsigned'
    trust = json.loads(trust_file.read_text(encoding='utf-8'))
    if not isinstance(trust,dict) or not trust.get('public_key'):
        raise ValueError('Signaturkontroll saknar betrodd publik nyckel')
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    tag,commit = release
    root = 'https://github.com/Tokke2/FTP-uploader/releases/download/'+tag+'/'
    manifest = fetch(root+'ftp-release-manifest.json')
    signature = base64.b64decode(fetch(root+'ftp-release-manifest.sig'),validate=True)
    key = Ed25519PublicKey.from_public_bytes(base64.b64decode(trust['public_key'],validate=True))
    key.verify(signature,manifest)
    data = json.loads(manifest)
    digest = hashlib.sha256()
    with open(archive,'rb') as stream:
        for block in iter(lambda: stream.read(1024*1024),b''): digest.update(block)
    if data.get('tag')!=tag or data.get('commit')!=commit or data.get('archive_sha256')!=digest.hexdigest():
        raise ValueError('Signerad manifest matchar inte vald release/arkiv')
    return 'ed25519-verified'
