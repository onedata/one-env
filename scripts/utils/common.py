"""
Utils for common operations.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import os
import re
import time
import shutil
import random
import string
import datetime
import fileinput
from typing import Optional, Tuple, List

from .terminal import warning
from .shell import call, check_output


def random_string(chars_num: int) -> str:
    return ''.join(random.choice(string.ascii_letters) for _ in
                   range(chars_num))


def replace_in_file_using_fileinput(file_path: str, pattern: str, value: str,
                                    backup: str = '',
                                    regexp: bool = False) -> None:
    with fileinput.FileInput(file_path, inplace=True, backup=backup) as file:
        for line in file:
            if regexp:
                print(re.sub(pattern, value, line), end='', flush=True)
            else:
                print(line.replace(pattern, value), end='', flush=True)


def replace_in_file_using_open(file_path, pattern, value):
    with open(file_path, 'r+') as file:
        content = file.read()
        content = re.sub(pattern, value, content)
        file.seek(0)
        file.truncate()
        file.write(content)


def force_create_directory(path: str) -> None:
    if os.path.exists(path):
        warning('Path {} already exists, it will be deleted'.format(path))
        shutil.rmtree(path)
    os.makedirs(path)


def unpack_tar(path: str, to_path: str) -> None:
    call(['tar', 'xzf', path], cwd=to_path)


def find_files_in_relative_paths(dirs: List[str],
                                 rel_paths: List[str]) -> Tuple[Optional[str],
                                                                List[str]]:
    cwd = os.getcwd()
    paths_to_check = [os.path.join(cwd, p) for p in dirs]
    for rel_path in rel_paths:
        paths_to_check.extend([os.path.join(cwd, rel_path, d) for d in dirs])
    location = next((path for path in paths_to_check if os.path.exists(path)),
                    None)

    return location, paths_to_check


def get_git_branch_cmd(path: str) -> str:
    return check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=path)


def get_git_repo(path: str) -> str:
    url = check_output(['git', 'config', '--get', 'remote.origin.url'],
                       cwd=path)
    return os.path.splitext(os.path.basename(url))[0]


def get_curr_time():
    return (datetime.datetime
            .fromtimestamp(time.time())
            .strftime('%Y.%m.%d-%H.%M.%S'))
