#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from config import readers, writers
from environment import application, node
import os
import argparse


def scenario_key(scenario):
    return {'scenario-1oz-1op': 'onedata-1p',
            'scenario-1oz-2op': 'onedata-2p'}.get(scenario)


class Env(object):
    def __init__(self, cfg, args, scenario):
        self.apps = []
        self.nodes = []

        cfg = cfg.get(scenario_key(os.path.basename(os.path.normpath(scenario))))

        if scenario:
            for service in cfg:
                prefix = cfg[service]['mountBinaries']['hostPathPrefix']
                nodes = cfg[service]['mountBinaries']['nodes']

                for n in nodes:
                    for app in n['binaries']:
                        project_path = app.get('hostPath', None)
                        project_path = os.path.join(prefix, project_path) \
                            if project_path else None
                        self.apps.append(application.Application(
                            app['name'], n['name'], project_path,
                            app.get('additionalArgs', None), service
                        ))

                    self.nodes.append(node.Node(n['name'], self.apps, args, service))
                    self.apps = []

        else:
            prefix = cfg['mountBinaries']['hostPathPrefix']
            nodes = cfg['mountBinaries']['nodes']

            # FIXME:
            for n in nodes:
                service = ''
                for app in n['binaries']:
                    if app['name'] == 'oz-panel':
                        service = 'onezone'
                        break
                    if app['name'] == 'op-panel':
                        service = 'oneprovider'
                        break

                for app in n['binaries']:
                    project_path = app.get('hostPath', None)
                    project_path = os.path.join(prefix, project_path) \
                        if project_path else None
                    self.apps.append(application.Application(
                        app['name'], n['name'], project_path,
                        app.get('additionalArgs', None),
                        service
                    ))

                self.nodes.append(
                    node.Node(n['name'], self.apps, args,
                              service))
                self.apps = []

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description='Bring up onedata environment.')


parser.add_argument(
    '--c', '-cfg_path',
    action='store',
    help='path to environment configuration file',
    dest='cfg_path')

parser.add_argument(
    '--o', '-out_dir',
    action='store',
    help='path to dir where configs should be written',
    default=os.getcwd(),
    dest='out_dir')

parser.add_argument(
    '-s', '-scenario',
    action='store',
    help='',
    default='',
    dest='scenario')


if __name__ == '__main__':
    args = parser.parse_args()

    # create yaml or json reader and read data
    reader = readers.ConfigReader(args.cfg_path)
    env_cfg = reader.load()

    # create config files
    env = Env(env_cfg, args, args.scenario)
