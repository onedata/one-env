import json
import yaml


class ConfigWriter:
    def __init__(self, cfg, format):
        if format == 'json':
            self.writer = JsonConfigWriter(cfg)
        else:
            self.writer = YamlConfigWriter(cfg)

    def dump(self):
        return self.writer.dump()


class JsonConfigWriter:
    def __init__(self, cfg):
        self.cfg = cfg

    def dump(self):
        print(json.dumps(self.cfg, indent=2, sort_keys=True))


class YamlConfigWriter:
    def __init__(self, cfg):
        self.cfg = cfg

    def dump(self):
        return yaml.safe_dump(self.cfg, default_flow_style=False)
