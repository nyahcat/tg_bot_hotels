import atexit
import platform
import shutil
import subprocess
from typing import List, Optional
import tempfile
import zipfile
import time
import os
from pathlib import Path
import requests
from loguru import logger


def run_ngrok() -> List[str]:
    """
    Запуск ngrok тоннеля к localhost.
    :return: tunnel_url: List[str] - url созданного тоннеля.
    """
    temp_ngrok_path = Path(tempfile.gettempdir())

    system = platform.system()
    if system == "Windows":
        command = "ngrok.exe"
    elif system == "Linux":
        command = "ngrok"
    elif system == "Darwin":
        command = "ngrok"
    else:
        raise SystemError(f'{system} не поддерживается')

    path_command = temp_ngrok_path / command
    exists = path_command.exists()
    logger.debug(f'exists {exists}')
    if not exists:
        download_ngrok(temp_ngrok_path, system)

    os.chmod(path_command, 755)

    ngrok = subprocess.Popen([path_command, 'http', '5000'])
    atexit.register(ngrok.terminate)
    time.sleep(3)
    localhost_url = "http://localhost:4040/api/tunnels"
    tunnel_url = requests.get(localhost_url)
    to_json = tunnel_url.json()

    tunnel_url = [i['public_url'] for i in to_json['tunnels'] if i['public_url'].startswith('https')]
    return tunnel_url


def download_ngrok(ngrok_path, system: str) -> None:
    """

    :param ngrok_path: Optional[Path] - путь до ngrok;
    :param system: str - название системы;
    :return: None.
    """
    logger.debug('download_ngrok reached')
    if Path(ngrok_path, 'ngrok').exists():
        logger.error(f'Path returned, cause {Path(ngrok_path)}')
        return
    if system == "Darwin":
        url = "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-darwin-amd64.zip"
    elif system == "Windows":
        url = "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-windows-amd64.zip"
    elif system == "Linux":
        url = "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip"
    else:
        raise SystemError(f'{system} не поддерживается')
    download_path = download_file(url)
    with zipfile.ZipFile(download_path, "r") as zip_ref:
        zip_ref.extractall(ngrok_path)


def download_file(url: str) -> Optional[Path]:
    """

    :param url: str - url загрузки;
    :return: Optional[Path] - путь к скачанному файлу.
    """
    local_filename = url.split('/')[-1]
    download_path = None
    try:
        with requests.get(url, stream=True) as response:
            if response.status_code == requests.codes.ok:
                download_path = Path(tempfile.gettempdir(), local_filename)
                with open(download_path, 'wb') as file:
                    shutil.copyfileobj(response.raw, file)
            else:
                response.raise_for_status()
    except requests.exceptions.HTTPError:
        logger.error('Something went wrong...')
    logger.debug(f'download_path {download_path}')
    return download_path
