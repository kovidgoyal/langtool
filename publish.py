#!/usr/bin/env python
# Publishes a release of langtool to PyPI (as kovidgoyal-langtool, the name langtool is
# taken there). The package is shipped as source only, so only an sdist is
# built and uploaded.

import glob
import os
import re
import shlex
import shutil
import subprocess
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join("src", "langtool", "__init__.py"), encoding="utf-8") as f:
    VERSION = re.search(
        r"""^__version__\s*=\s*['"]([^'"]+)['"]""", f.read(), re.M
    ).group(1)


def red(text):
    return "\033[91;1m" + text + "\033[39;22m"


def green(text):
    return "\033[92;1m" + text + "\033[39;22m"


def run(*cmd):
    if len(cmd) == 1:
        cmd = shlex.split(cmd[0])
    print(green(" ".join(cmd)))
    ret = subprocess.Popen(cmd).wait()
    if ret != 0:
        raise SystemExit(ret)


def build_release():
    for rem in "dist build".split():
        os.path.exists(rem) and shutil.rmtree(rem)
    run(sys.executable, "-m", "build", "--sdist")
    run("twine", "check", "--strict", *glob.glob("dist/*"))


def tag_release():
    run('git tag -f -s "v{0}" -m "version-{0}"'.format(VERSION))
    run('git push -f origin "v{0}"'.format(VERSION))


def upload_release():
    files = list(glob.glob("dist/*"))
    cmd = ["twine", "upload"]
    if "PENV" in os.environ:
        cmd += ["--config-file", os.path.join(os.environ["PENV"], "pypi")]
    run(*cmd, *files)


def has_executable(exe):
    for path in os.environ["PATH"].split(os.pathsep):
        if os.access(os.path.join(path, exe), os.X_OK):
            return True
    return False


def main():
    if not has_executable("twine"):
        raise SystemExit("Need to install twine to upload to PyPI")
    if (
        subprocess.run(
            [sys.executable, "-c", "import build"], capture_output=True
        ).returncode
        != 0
    ):
        raise SystemExit("Need to install build to build the release")
    if input("Publish version {} [y/n]? ".format(red(VERSION))) != "y":
        raise SystemExit(1)
    build_release()
    if input(red("Upload") + " release [y/n]? ") != "y":
        raise SystemExit(1)
    tag_release()
    upload_release()


if __name__ == "__main__":
    main()
