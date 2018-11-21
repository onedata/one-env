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


def replace_in_file(file_path: str, pattern: str, value: str,
                    backup: str = '', regexp: bool = False) -> None:
    with fileinput.FileInput(file_path, inplace=True, backup=backup) as file:
        for line in file:
            if regexp:
                print(re.sub(pattern, value, line), end='')
            else:
                print(line.replace(pattern, value), end='')
