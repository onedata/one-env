#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import yaml


class ConfigReader(object):
    def __init__(self, path):
        filename, extension = os.path.splitext(path)
        if extension in ['.yml', '.yaml']:
            self.reader = YamlConfigReader(path)
        else:
            self.reader = JsonConfigReader(path)

    def load(self):
        return self.reader.load()


class JsonConfigReader(object):
    def __init__(self, path):
        self.path = path

    def load(self):
        with open(self.path) as f:
            return json.load(f)


class YamlConfigReader(object):
    def __init__(self, path):
        self.path = path

    def load(self):
        with open(self.path) as f:
            return yaml.load(f)
