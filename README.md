# Usage

PyAdvisor is a simple cgroup monitor tool and include core features from cAdvisor, it work with `crontab` and `netcat`, so you can easily to custom a metrics pipeline then send to the graphite server.

```shell
MAILTO=admin@example.com
* * * * * python /opt/pyadvisor.py --format graphite --cpu --memory --io --docker /home/q/docker --docker_only | nc graphite.example.com 2013
```

Here is full help message

```shell
usage: pyadvisor [-h] [-v] [-f {statsd,graphite}] [-c] [-m] [-d] [-n] [-i]
                 [-D DOCKER] [-p PREFIX] [--docker_only]

cAdvisor distribution via Python.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -f {statsd,graphite}, --format {statsd,graphite}
                        Output format for container metrics
  -c, --cpu             Monitor CPU
  -m, --memory          Monitor memory
  -d, --disk            Monitor disk
  -n, --network         Monitor network
  -i, --io              Monitor block device io
  -D DOCKER, --docker DOCKER
                        Docker home
  -p PREFIX, --prefix PREFIX
                        Metric prefix
  --docker_only         Only collect docker metric
```

PyAdvisor support graphite/statsd output format via `-f` or `--format`, so you can run the script like this:
```shell
$ python pyadvisor.py -f statsd
pycadvisor.c3_session.cpu.usage:1434319785|g
pycadvisor.c3_session.cpu.usage_percpu.1:104893690|g
pycadvisor.c3_session.cpu.usage_percpu.0:74241032|g
pycadvisor.c3_session.cpu.usage_percpu.3:39300375|g
pycadvisor.c3_session.cpu.usage_percpu.2:562260356|g
pycadvisor.c3_session.cpu.usage_percpu.5:199176933|g
pycadvisor.c3_session.cpu.usage_percpu.4:345035182|g
pycadvisor.c3_session.cpu.usage_percpu.7:20531154|g
pycadvisor.c3_session.cpu.usage_percpu.6:88881063|g
pycadvisor.c3_session.memory.failcnt:0|g
pycadvisor.c3_session.memory.limit_in_bytes:18446744073709551615|g
pycadvisor.c3_session.memory.swap:0|g
pycadvisor.c3_session.memory.memsw.failcnt:-1|g
pycadvisor.c3_session.memory.usage_in_bytes:20480|g
pycadvisor.c3_session.memory.kmem.max_usage_in_bytes:0|g
pycadvisor.c3_session.memory.max_usage_in_bytes:58257408|g
pycadvisor.c3_session.memory.kmem.usage_in_bytes:0|g
pycadvisor.c3_session.memory.cache:20480|g
pycadvisor.c3_session.memory.mapped_file:0|g
pycadvisor.c3_session.memory.kmem.limit_in_bytes:18446744073709551615|g
pycadvisor.c3_session.memory.memsw.limit_in_bytes:-1|g
pycadvisor.c3_session.memory.kmem.failcnt:0|g
pycadvisor.c3_session.memory.memsw.usage_in_bytes:-1|g
pycadvisor.c3_session.memory.pgpgout:9980|g
pycadvisor.c3_session.memory.pgfault:22823|g
pycadvisor.c3_session.memory.pgpgin:8963|g
pycadvisor.c3_session.memory.memsw.max_usage_in_bytes:-1|g
pycadvisor.c3_session.cpu.share:1024|g
pycadvisor.c3_session.cpu.cfs_quota_us:-1|g
pycadvisor.c2_session.cpu.share:1024|g
pycadvisor.c2_session.cpu.cfs_quota_us:-1|g
$ python pyadvisor -f graphite
pycadvisor.c3_session.cpu.usage 1434319785 1471416281
pycadvisor.c3_session.cpu.usage_percpu.1 104893690 1471416281
pycadvisor.c3_session.cpu.usage_percpu.0 74241032 1471416281
pycadvisor.c3_session.cpu.usage_percpu.3 39300375 1471416281
pycadvisor.c3_session.cpu.usage_percpu.2 562260356 1471416281
pycadvisor.c3_session.cpu.usage_percpu.5 199176933 1471416281
pycadvisor.c3_session.cpu.usage_percpu.4 345035182 1471416281
pycadvisor.c3_session.cpu.usage_percpu.7 20531154 1471416281
pycadvisor.c3_session.cpu.usage_percpu.6 88881063 1471416281
pycadvisor.c3_session.memory.failcnt 0 1471416281
pycadvisor.c3_session.memory.limit_in_bytes 18446744073709551615 1471416281
pycadvisor.c3_session.memory.swap 0 1471416281
pycadvisor.c3_session.memory.memsw.failcnt -1 1471416281
pycadvisor.c3_session.memory.usage_in_bytes 20480 1471416281
pycadvisor.c3_session.memory.kmem.max_usage_in_bytes 0 1471416281
pycadvisor.c3_session.memory.max_usage_in_bytes 58257408 1471416281
pycadvisor.c3_session.memory.kmem.usage_in_bytes 0 1471416281
pycadvisor.c3_session.memory.cache 20480 1471416281
pycadvisor.c3_session.memory.mapped_file 0 1471416281
pycadvisor.c3_session.memory.kmem.limit_in_bytes 18446744073709551615 1471416281
pycadvisor.c3_session.memory.memsw.limit_in_bytes -1 1471416281
pycadvisor.c3_session.memory.kmem.failcnt 0 1471416281
pycadvisor.c3_session.memory.memsw.usage_in_bytes -1 1471416281
pycadvisor.c3_session.memory.pgpgout 9980 1471416281
pycadvisor.c3_session.memory.pgfault 22823 1471416281
pycadvisor.c3_session.memory.pgpgin 8963 1471416281
pycadvisor.c3_session.memory.memsw.max_usage_in_bytes -1 1471416281
pycadvisor.c3_session.cpu.share 1024 1471416281
pycadvisor.c3_session.cpu.cfs_quota_us -1 1471416281
```

enjoy it !
