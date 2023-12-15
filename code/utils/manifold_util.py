import hashlib
import os
import subprocess
import time


def run_command(cmd: str, retries=0) -> None:
    print(f"Running command: {cmd}")
    for k in range(retries + 1):
        retc = os.system(cmd)
        if retc == 0:
            return
        time.sleep(1)
        if k == retries:
            raise RuntimeError(
                f'Command "{cmd}" failed with return code {retc} after {retries} retries.'
            )


def subprocess_run_command(cmd):
    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    assert result.returncode == 0, result.stderr


def is_manifold_path(p: str) -> bool:
    return p.startswith("manifold://")


def get_manifold_path(p: str) -> str:
    if p.startswith("manifold://"):
        return p.split("//")[1]
    return p


def manifold_get_file(manifold_path: str, dest_file) -> None:
    path = get_manifold_path(manifold_path)
    cmd = f"manifold --prod-use-cython-client get {path} {dest_file} --overwrite"
    subprocess_run_command(cmd)


def manifold_put_dir(local_dir: str, remote_dir) -> None:
    remote_dir = get_manifold_path(remote_dir)
    cmd = f"manifold --prod-use-cython-client putr {local_dir} {remote_dir} --overwrite"
    subprocess_run_command(cmd)


def manifold_mkdirs(remote_dir) -> None:
    remote_dir = get_manifold_path(remote_dir)
    cmd = f"manifold mkdirs {remote_dir}"
    subprocess_run_command(cmd)


def str_hash(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def download_if_on_manifold(path: str, tmp_dir: str = "./") -> str:
    if is_manifold_path(path):
        local_path = os.path.join(tmp_dir, str_hash(path))
        if not os.path.exists(local_path):
            manifold_get_file(path, local_path)
        return local_path
    else:
        return path


class ManifoldUploader:
    """
    Map a manifold dir to a local directory and upload it when the object is destroyed
    """

    def __init__(self, manifold_dir: str, tmp_dir: str = "./", verbose: bool = False):
        self._verbose = verbose
        self.manifold_dir = manifold_dir
        self._tmp_dir = tmp_dir
        self.local_dir = os.path.join(tmp_dir, str_hash(manifold_dir))
        if not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)

    def __del__(self):
        if self._verbose:
            print(f"Uploading to {self.manifold_dir}")
        manifold_put_dir(self.local_dir, self.manifold_dir)
