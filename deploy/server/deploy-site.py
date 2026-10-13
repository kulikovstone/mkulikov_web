#!/usr/bin/python3
"""Root-owned SSH forced command; runs as the unprivileged deploy user."""

import fcntl
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile

BASE = Path('/var/www/mkulikov')
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_CONTENT_BYTES = 100 * 1024 * 1024
MAX_FILES = 2000


def unpack_site(destination):
    archive = sys.stdin.buffer.read(MAX_ARCHIVE_BYTES + 1)
    if not archive or len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError('Archive is empty or exceeds 20 MiB')

    total_size = 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r|gz') as bundle:
        for count, member in enumerate(bundle, start=1):
            if count > MAX_FILES:
                raise ValueError('Too many archive entries')
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Invalid archive path')
            if any(part.startswith('.') for part in path.parts):
                raise ValueError('Hidden files are not website assets')
            if not member.isdir() and not member.isfile():
                raise ValueError('Only regular files and directories are allowed')
            total_size += member.size
            if member.size < 0 or total_size > MAX_CONTENT_BYTES:
                raise ValueError('Unpacked site exceeds 100 MiB')

            target = destination.joinpath(*path.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True, mode=0o755)
            else:
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                with bundle.extractfile(member) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o644)

    index = destination / 'index.html'
    if not index.is_file() or not index.stat().st_size:
        raise ValueError('The build must contain a nonempty index.html')


def check_published_index(release):
    # Проверяем HTTPS с правильным именем сертификата через локальный Nginx.
    response = subprocess.run(
        ['curl', '--fail', '--silent', '--show-error', '--max-time', '15',
         '--resolve', 'mkulikov.com:443:127.0.0.1',
         'https://mkulikov.com/'],
        check=True, capture_output=True, timeout=20,
    )
    expected = hashlib.sha256((release / 'index.html').read_bytes()).digest()
    actual = hashlib.sha256(response.stdout).digest()
    if actual != expected:
        raise RuntimeError('HTTPS returned a different version of index.html')


def publish(release_id):
    releases = BASE / 'releases'
    release = releases / release_id
    current = BASE / 'current'
    next_link = BASE / ('.current-' + release_id)
    if release.exists() or next_link.exists() or next_link.is_symlink():
        raise ValueError('Release already exists; rerun the GitHub job for a new attempt ID')
    if not current.is_symlink():
        raise ValueError('Expected the existing current symlink')
    previous = os.readlink(current)
    staging = Path(tempfile.mkdtemp(prefix='.upload-', dir=releases))
    switched = False
    try:
        unpack_site(staging)
        staging.chmod(0o755)
        staging.rename(release)
        next_link.symlink_to(Path('releases') / release_id)
        os.replace(next_link, current)
        switched = True
        check_published_index(release)
    except Exception:
        if switched:
            next_link.symlink_to(previous)
            os.replace(next_link, current)
            print(f'Previous version restored: {previous}', file=sys.stderr)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        next_link.unlink(missing_ok=True)

    print(f'Published: {release_id}')
    print(f'Previous: {previous}')
    print('HTTPS content check: OK')


def main():
    command = shlex.split(os.environ.get('SSH_ORIGINAL_COMMAND', ''))
    if len(command) != 2 or command[0] != 'deploy':
        raise ValueError('Only deploy <commit>-<run-id>-<attempt> is allowed')
    release_id = command[1]
    if not re.fullmatch(r'[a-f0-9]{40}-[0-9]+-[0-9]+', release_id):
        raise ValueError('Invalid release identifier')

    os.umask(0o022)
    with (BASE / '.deploy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        publish(release_id)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Deployment failed: {error}', file=sys.stderr)
        sys.exit(1)
