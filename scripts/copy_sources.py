import cmd
import sources as s
import pods
import os

OZ_SOURCES = ['oz-worker', 'oz-panel', 'cluster-manager']
OP_SOURCES = ['op-worker', 'op-panel', 'cluster-manager']


def main():
    for pod_name in ['dev-onezone-0']:
        service = 'onezone' if 'onezone' in pod_name else 'oneprovider'
        sources = OZ_SOURCES if 'onezone' in pod_name else OP_SOURCES

        for source in sources:
            source_path = os.path.abspath(s.locate(source, service, pod_name))
            cmd.call(['kubectl', 'exec', '-it', pod_name, '--', 'mkdir', '-p', '{}'.format(os.path.dirname(source_path))])
            cmd.call(pods.cmd_copy_to_pod(pod_name, source_path, source_path))
        cmd.call(pods.cmd_copy_to_pod(pod_name, '/home/michal/.one-env',
                                      '/home/michal/.one-env'))
        cmd.call(['kubectl', 'exec', '-it', pod_name, '--', 'touch', '/tmp/sources_mounted'])


if __name__ == "__main__":
    main()

