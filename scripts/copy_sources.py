import cmd_utils
import sources as s
import pods
import os
import deployments_dir as dd
import argparse
import subprocess
import console


SCRIPT_DESCRIPTION = 'Rsync local directory with directory in pod'

parser = argparse.ArgumentParser(
    prog='onenv rsync',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    description=SCRIPT_DESCRIPTION
)


args = parser.parse_args()


def rsync(pod, source, dest):
    rsync_cmd = ['rsync -av --blocking-io --rsync-path={} --rsh=\'kubectl '
                 'exec {} -i -- \' {}/ rsync:.'.format(dest, pod, source)]
    print(rsync_cmd)

    subprocess.call(rsync_cmd, shell=True)
    console.info('Done')


OZ_SOURCES = ['oz-panel', 'cluster-manager', 'oz-worker']
OP_SOURCES = ['op-panel', 'cluster-manager', 'op-worker']


def main():
    for pod_name in ['dev-onezone-0']:
        service = 'onezone' if 'onezone' in pod_name else 'oneprovider'
        sources = OZ_SOURCES if 'onezone' in pod_name else OP_SOURCES

        one_env_dir = os.path.expanduser('~/.one-env')

        cmd_utils.call(['kubectl', 'exec', '-it', pod_name, '--', 'mkdir', '-p', one_env_dir])
        rsync(pod_name, one_env_dir, one_env_dir)

        for source in sources:
            source_path = os.path.abspath(s.locate(source, service, pod_name))
            cmd_utils.call(['kubectl', 'exec', '-it', pod_name, '--', 'mkdir', '-p',
                            source_path])

            # For now copying sources to the same path as sources path on host
            rsync(pod_name, source_path, source_path)

        cmd_utils.call(['kubectl', 'exec', '-it', pod_name, '--', 'touch', '/tmp/sources_mounted'])


if __name__ == "__main__":
    main()

