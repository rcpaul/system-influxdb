from datetime import datetime

import psutil
import yaml
import math
import time

from influxdb_client import InfluxDBClient, Point, WritePrecision, WriteOptions

class MeasurementSensor():
    """Superclass for all sensors"""

    lastValues = {}
    lastUpdates = {}

    def __init__(self, *args, **kwargs):
        config = kwargs['config']

    def upload(self, tag, value=0):
        epochint = math.floor(time.time())

        if tag not in self.lastUpdates:
            self.lastUpdates[tag] = epochint

        if tag not in self.lastValues:
            self.lastValues[tag] = None

        if self.lastValues[tag] != value or self.lastUpdates[tag] + 3600 < epochint:
            print("{} = {}".format(tag, value))

            p = Point(type(self).__name__).tag("tag", tag).tag("system", globalConfig['system']).field("value", value).time(datetime.utcnow(), WritePrecision.S)
            influxWriteApi.write(org=globalConfig['org'], bucket=globalConfig['bucket'], record=p)

            self.lastValues[tag] = value
            self.lastUpdates[tag] = epochint

    def readString(self, path):
        with open(path, 'r') as f:
            return f.read()

    def readInteger(self, path):
        with open(path, 'r') as f:
            raw = f.read()
            integer = int(raw)
            return integer

class LoadSensor(MeasurementSensor):
    """Sensor for load"""

    def tick(self):
        load = psutil.getloadavg()[0];
        self.upload("load-1", load)

class CpuUsageSensor(MeasurementSensor):
    """Sensor for CPU usage"""

    def tick(self):
        usage = psutil.cpu_percent()
        self.upload("usage", usage)

class CpuMaxTemperatureSensor(MeasurementSensor):
    """Sensor for the maximum temperature all cores"""

    def tick(self):
        maxTemp = 0
        for core in psutil.sensors_temperatures()['coretemp']:
            if core.current > maxTemp: maxTemp = core.current

        self.upload("maxtemp", maxTemp)

class MemoryUsageSensor(MeasurementSensor):
    """Sensor for percentage of system memory in use"""
    def tick(self):
        usage = psutil.virtual_memory().percent
        self.upload("perc", usage)

class NetworkThroughputSensor(MeasurementSensor):
    """Sensor for network throughput"""

    init = False
    r1 = None
    t1 = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = kwargs['config']
        self.interface = config['interface']
        
    def tick(self):
        r2 = self.readInteger('/sys/class/net/' + self.interface + '/statistics/rx_bytes')
        t2 = self.readInteger('/sys/class/net/' + self.interface + '/statistics/tx_bytes')

        if not self.init:
            self.r1 = r2
            self.t1 = t2
            self.init = True
            return

        r = r2 - self.r1
        self.upload("{}-rx".format(self.interface), r)

        t = t2 - self.t1
        self.upload("{}-tx".format(self.interface), t)

        self.r1 = r2
        self.t1 = t2

class DiskTroughputSensor(MeasurementSensor):
    """Sensor for disk throughput"""

    init = False
    r1 = None
    w1 = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = kwargs['config']
        self.device = config['device']
        
    def tick(self):
        stat = self.readString('/sys/block/' + self.device + '/stat').split()
        r2 = int(stat[2])
        w2 = int(stat[6])

        if not self.init:
            self.r1 = r2
            self.w1 = w2
            self.init = True
            return

        r = round((r2 - self.r1) * .5)
        self.upload("{}-read".format(self.device), r)
        
        w = round((w2 - self.w1) * .5)
        self.upload("{}-write".format(self.device), w)

        self.r1 = r2
        self.w1 = w2

class DiskSpaceSensor(MeasurementSensor):
    """Sensor for disk space"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = kwargs['config']
        self.path = config['path']

    def tick(self):
        usage = psutil.disk_usage(self.path).percent
        self.upload("{}".format(self.path), usage)

class Controller():
    """Main controller and instantiation of all sensors"""

    def __init__(self, config):
        sensorClasses = {
            'load': LoadSensor,
            'cpu-usage': CpuUsageSensor,
            'cpu-max-temperature': CpuMaxTemperatureSensor,
            'memory-usage': MemoryUsageSensor,
            'network-throughput': NetworkThroughputSensor,
            'disk-throughput': DiskTroughputSensor,
            'disk-space': DiskSpaceSensor,
        }

        self.sensors = []
        for sensorItem in config['sensors']:
            if isinstance(sensorItem, str):
                sensor = sensorClasses[sensorItem](config=None)
                self.sensors.append(sensor)
            else:
                sensorName = next(iter(sensorItem))
                sensorConfig = sensorItem[sensorName]
                sensor = sensorClasses[sensorName](config=sensorConfig)
                self.sensors.append(sensor)

    def tick(self):
        while True:
            for sensor in self.sensors:
                try:
                    sensor.tick()
                except:
                    print("Ignoring error for sensor {}".format(sensor))

            # Schedule update at next wall clock second
            delay = round((1000000 - datetime.now().microsecond) / 1000)
            time.sleep(delay / 1000)

globalConfig = None
with open('config.yml') as file:
    globalConfig = yaml.load(file, Loader=yaml.FullLoader)

influxClient = InfluxDBClient(url=globalConfig['url'], token=globalConfig['token'])
influxWriteApi = influxClient.write_api(write_options=WriteOptions(flush_interval=20_000))

controller=Controller(globalConfig)
controller.tick()
