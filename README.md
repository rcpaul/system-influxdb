# system-influxdb
Import vital information into InfluxDB. Support for
- 1 minute average system load
- CPU usage (percentage)
- Maximum temperature amongst all CPU cores
- Memory usage (percentage)
- Network throughput
- Disk throughput
- Disk space

Sample configuration to be placed in `config.yml`:

    indicators:
    - load:
    - cpu-usage:
    - cpu-max-temperature:
    - memory-usage:
    - network-throughput:
        interface: enp7s0f1
    - disk-throughput:
        device: nvme0n1
    - disk-throughput:
        device: sda
    - disk-space:
        path: /hdd

    url: http://192.168.178.10:8086
    token: "..."
    org: "organization"
    bucket: "name-of-bucket"
    system: "name-of-system"
