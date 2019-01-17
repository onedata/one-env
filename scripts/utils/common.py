"""
Utils for common operations.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import re
import random
import string
import fileinput


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
