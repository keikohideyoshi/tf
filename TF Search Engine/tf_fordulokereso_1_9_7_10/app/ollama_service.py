"""Start a user-owned Ollama process without requiring administrator rights."""
import shutil
import subprocess
import sys
import time
import urllib.request

URL = 'http://127.0.0.1:11434/api/tags'


def running(timeout=1.0):
    try:
        with urllib.request.urlopen(URL, timeout=timeout) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def start(wait_seconds=15):
    """Return (status, detail); status: already_running, started, missing, failed."""
    if running():
        return 'already_running', 'Az Ollama már fut.'
    executable = shutil.which('ollama')
    if not executable:
        return 'missing', 'Az Ollama nincs telepítve vagy nem található a PATH változóban.'
    try:
        options = {'stdin': subprocess.DEVNULL, 'stdout': subprocess.DEVNULL,
                   'stderr': subprocess.DEVNULL, 'start_new_session': True}
        if sys.platform == 'win32':
            options.pop('start_new_session')
            options['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
        process = subprocess.Popen([executable, 'serve'], **options)
    except OSError as exc:
        return 'failed', f'Nem sikerült elindítani az Ollamát: {exc}'
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if running(timeout=0.5):
            return 'started', 'Az Ollama elindult és elérhető.'
        if process.poll() is not None:
            return 'failed', ('Az Ollama folyamata leállt. Lehet, hogy a portot másik '
                              'folyamat használja, vagy a szolgáltatás hibásan indul.')
        time.sleep(0.3)
    return 'failed', ('Az Ollama indítását kezdeményeztük, de a szolgáltatás '
                      '15 másodpercen belül nem vált elérhetővé.')
