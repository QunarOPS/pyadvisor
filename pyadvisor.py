# -*- coding: utf-8 -*-
import argparse
import json
import time
import os
import re
# import subprocess

__version__ = '0.0.3'
memory_prefix_mapping = {'': 'memory_usage', 'kmem': 'kernel_memory_usage', 'memsw': 'swap_memory_usage'}
# low version docker will create a docker-<container_id>.scope dir
docker_pattern = re.compile(r'([a-z0-9]{64})|docker\-([a-z0-9]{64})\.scope')
dm_pattern = re.compile(r'^dm-\d+$')


def get_cgroups_mountinfo():
    """
    获取cgroup挂载信息
    :return: dict(subsystem -> cgroup_path)
    """
    mount_points = dict()
    with open('/proc/self/mountinfo', 'r') as f:
        for mountinfo in f:
            data = mountinfo.split(' ')
            if len(data) == 11:
                # CentOS7 has a extra field named 'shared:%d'
                mount_point, fs_type, source = data[4], data[8], data[9]
            else:
                mount_point, fs_type, source = data[4], data[7], data[8]
            if fs_type == 'cgroup' and source == 'cgroup':
                _, subsystem = mount_point.rsplit('/', 1)
                # CentOS7 merge cpu & cpuacct subsystem, WTF!
                if ',' in subsystem:
                    for tmp in subsystem.split(','):
                        mount_points[tmp] = mount_point
                mount_points[subsystem] = mount_point
    return mount_points


def get_enabled_cgroup():
    """
    获取enabled cgroup
    :return: dict(subsystem -> bool)
    """
    enabled_cgroups = dict()
    with open('/proc/cgroups', 'r') as f:
        for cgroup_enable_info in f:
            if not cgroup_enable_info.startswith('#'):
                subsystem, _, _, enabled = cgroup_enable_info.split('\t')
                enabled_cgroups[subsystem] = enabled
    return enabled_cgroups


def get_supported_cgroup(opts):
    """
    获取允许从cgroup采集信息
    :param opts: settings
    :return: list(subsystem)
    """
    supported_cgroups = list()
    if opts.cpu:
        supported_cgroups.append('cpu')
        supported_cgroups.append('cpuacct')
        supported_cgroups.append('cpuset')
    if opts.memory:
        supported_cgroups.append('memory')
    if opts.io:
        supported_cgroups.append('blkio')
    return supported_cgroups


def get_supported_cgroups(opts):
    """
    获取要监控的cgroup信息
    :param opts: settings
    :return: dict(subsystem -> path)
    """
    cgroups = get_cgroups_mountinfo()
    enabled_cgroups = get_enabled_cgroup()
    for subsystem, _ in cgroups.items():
        if subsystem not in enabled_cgroups:
            del cgroups[subsystem]
    supported_cgroups = get_supported_cgroup(opts)
    for subsystem, _ in cgroups.items():
        if subsystem not in supported_cgroups:
            del cgroups[subsystem]
    return cgroups


def get_metrics_from_cgroup(opts):
    """
    迭代每一个cgroup的指标
    :param opts: settings
    :return: generator
    """
    cgroups = get_supported_cgroups(opts)
    for subsystem, cgroup_path in cgroups.items():
        for path, sub_dirs, _ in os.walk(cgroup_path):
            if not sub_dirs:
                # 先判断是否为docker容器
                name = path[path.rindex('/') + 1:]
                match = docker_pattern.match(name)
                if match is not None:
                    name = match.group(1) if match.group(1) is not None else match.group(2)
                    alias = get_docker_alias(name, opts)
                elif opts.docker_only:
                    continue
                else:
                    alias = get_raw_container_alias(path)
                yield get_metrics(alias, subsystem, path)
            else:
                continue


def get_docker_alias(name, opts):
    """
    解析容器名字，找不到环境变量就返回目录名
    :param path: cgroup目录
    :param opts: settings
    :return: string
    """
    # 可能是Docker
    if name in os.listdir(os.path.join(opts.docker, 'containers')):
        # id出现在了docker home内
        container_home = os.path.join(opts.docker, 'containers', name)
        # 读config.json获取环境变量
        if os.path.isfile(os.path.join(container_home, 'config.v2.json')):
            config_file_path = os.path.join(container_home, 'config.v2.json')
        else:
            config_file_path = os.path.join(container_home, 'config.json')
        # 读取env，取得MESOS_TASK_ID
        with open(os.path.join(container_home, config_file_path), 'r') as config:
            inspect_json = json.load(config)
            envs = inspect_json['Config']['Env']
            if envs is not None:
                for env in envs:
                    key, value = env.split('=')
                    if key == 'MESOS_TASK_ID':
                        return value
            return inspect_json['Name'][1:]
    return name


def get_raw_container_alias(path):
    """
    解析容器名字，找不到环境变量就返回目录名
    :param path: cgroup目录
    :param opts: settings
    :return: string
    """
    # 非Docker读取/proc/<pid>/environ文件，解析环境变量
    with open(os.path.join(path, 'cgroup.procs')) as procs:
        env_file_path = os.path.join('proc', procs.readline().strip(), 'environ')
        if os.path.isfile(env_file_path):
            with open(env_file_path, 'r') as envs:
                env_kvs = envs.readline().strip().split('\x00')
                for kvs in env_kvs:
                    key, value = kvs.split('=')
                    if key == 'MESOS_TASK_ID':
                        return value
    return path[path.rindex('/') + 1:].replace('.', '_')


def get_metrics(alias, subsystem, path):
    if subsystem == 'cpu':
        ret = {
            '%s.cpu.share' % alias: read_first_line(os.path.join(path, 'cpu.shares')),
            '%s.cpu.cfs_quota_us' % alias: read_first_line(os.path.join(path, 'cpu.cfs_quota_us')),
            '%s.cpu.cfs_period_us' % alias: read_first_line(os.path.join(path, 'cpu.cfs_period_us')),
        }
        return ret
    if subsystem == 'cpuset':
        # cpuset值不统计，因为watcher的图表不好展示这种占位信息
        pass
    if subsystem == 'cpuacct':
        ret = {
            '%s.cpu.usage' % alias: read_first_line(os.path.join(path, 'cpuacct.usage')),
        }
        for idx, usage in enumerate(read_first_line(os.path.join(path, 'cpuacct.usage_percpu')).split(' ')):
            ret['%s.cpu.usage_percpu.%d' % (alias, idx)] = usage
        return ret
    if subsystem == 'memory':
        memory_stat = read_all_lines(os.path.join(path, 'memory.stat'))
        ret = {
            '%s.memory.cache' % alias: memory_stat.get('cache', 0),
            '%s.memory.swap' % alias: memory_stat.get('swap', 0),
            '%s.memory.mapped_file' % alias: memory_stat.get('mapped_file', 0),
            '%s.memory.pgpgin' % alias: memory_stat.get('pgpgin', 0),
            '%s.memory.pgpgout' % alias: memory_stat.get('pgpgout', 0),
            '%s.memory.pgfault' % alias: memory_stat.get('pgfault', 0),
        }
        for prefix, value in memory_prefix_mapping.items():
            module_name = '%s.%s' % ('memory', prefix) if prefix else 'memory'
            usage_file = '%s.%s' % (module_name, 'usage_in_bytes')
            max_usage_file = '%s.%s' % (module_name, 'max_usage_in_bytes')
            failcnt_file = '%s.%s' % (module_name, 'failcnt')
            total_bytes = '%s.%s' % (module_name, 'limit_in_bytes')
            ret['%s.%s' % (alias, usage_file)] = read_first_line(os.path.join(path, usage_file))
            ret['%s.%s' % (alias, max_usage_file)] = read_first_line(os.path.join(path, max_usage_file))
            ret['%s.%s' % (alias, failcnt_file)] = read_first_line(os.path.join(path, failcnt_file))
            ret['%s.%s' % (alias, total_bytes)] = read_first_line(os.path.join(path, total_bytes))
        # soft limit
        ret['%s.memory.soft_limit_in_bytes' % alias] = read_first_line(os.path.join(path, 'memory.soft_limit_in_bytes'))

        return ret
    if subsystem == 'blkio':
        devices = get_block_devices_mapping()
        # major, minor, operation(read, write, sync, or async), and bytes.
        ret = get_block_devices_metrics(alias, os.path.join(path, 'blkio.throttle.io_service_bytes'), devices)
        # major, minor, operation(read, write, sync, or async), and numbers.
        ret.update(get_block_devices_metrics(alias, os.path.join(path, 'blkio.throttle.io_serviced'), devices))
        return ret


def get_block_devices_metrics(alias, path, devices):
    ret = {}
    suffix = 'bytes' if path[path.rindex('_') + 1:] == 'bytes' else 'io'
    with open(path, 'r') as f:
        for line in f:
            data = line.strip().split(' ')
            if len(data) == 2:
                continue
            device, action, value = data[0], data[1], data[2]
            if device in devices:
                ret['%s.%s.%s.%s' % (alias, devices[device], action.lower(), suffix)] = value
    return ret


def get_block_devices_mapping():
    ret = {}
    for _, devices, __ in os.walk('/sys/dev/block'):
        if devices:
            for dev in devices:
                target = os.readlink(os.path.join('/sys/dev/block', dev))
                ret[dev] = target[target.rindex('/') + 1:]
    return ret


def read_all_lines(file_path):
    if os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            data = {}
            for line in f:
                key, value = line.strip().split(' ')
                data[key] = value
            return data
    else:
        return None


def read_first_line(file_path):
    if os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            line = f.readline().strip()
            return line if line else '-1'
    else:
        return '-1'


def format(metrics, format='statsd', prefix='pyadvisor'):
    """
    格式化打印指标到stdout
    :param metrics: 指标
    :param format: 格式{statsd, graphite}
    :param prefix: 指标名前缀
    :return:
    """
    if metrics is None:
        return

    if format == 'statsd':
        for key, value in metrics.items():
            print '%s.%s:%s|g' % (prefix, key, value)
    elif format == 'graphite':
        ts = int(time.time())
        for key, value in metrics.items():
            print '%s.%s %s %d' % (prefix, key, value, ts)
    else:
        pass


def parse_args():
    """
    支持格式化输出和自定义指标收集
    :return:
    """
    parser = argparse.ArgumentParser(description='cAdvisor distribution via Python.', prog='pyadvisor')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('-f', '--format', help='Output format for container metrics',
                        choices={'statsd', 'graphite'}, default='statsd')
    parser.add_argument('-c', '--cpu', help='Monitor CPU', action='store_true', default=True)
    parser.add_argument('-m', '--memory', help='Monitor memory', action='store_true', default=True)
    parser.add_argument('-d', '--disk', help='Monitor disk', action='store_true', default=False)
    # --net=host模式下无法监控容器网卡流量
    parser.add_argument('-n', '--network', help='Monitor network', action='store_true', default=False)
    parser.add_argument('-i', '--io', help='Monitor block device io', action='store_true', default=False)
    parser.add_argument('-D', '--docker', help='Docker home', default='/var/lib/docker')
    parser.add_argument('-p', '--prefix', help='Metric prefix', default='pycadvisor')
    parser.add_argument('--docker_only', action='store_true', default=False, help='Only collect docker metrics')
    return parser.parse_args()


def main(opts):
    for metrics in get_metrics_from_cgroup(opts):
        if metrics:
            format(metrics, format=opts.format, prefix=opts.prefix)

    if opts.disk:
        raise NotImplementedError('Would be implemented in next release.')


if __name__ == '__main__':
    main(parse_args())
