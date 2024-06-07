#!/usr/bin/python
import datetime
import os
import sys
import time
import csv

import urllib3

urllib3.disable_warnings()

import hexoskin.client
import hexoskin.errors

class DataPoller(object):
    """An example of an approach for polling for realtime data in a cache-
    friendly fashon."""

    def __init__(self, api, datatypes, **kwargs):
        self.since = 0
        self.window = 256 * 60 * 10
        self.api = api
        self.datatypes = datatypes
        self.filter_args = kwargs

    def poll(self):
        now = int(time.mktime(datetime.datetime.now().timetuple())) * 256
        if now - self.since > self.window:
            self.since = now
        self.filter_args.update({'start': self.since, 'end': self.since + self.window})
        result = self.api.data.list(datatype__in=self.datatypes, **self.filter_args)
        if result:
            self.since = max([max(v)[0] for d, v in result[0].data.items()])
            if len(result[0].data.itervalues().next()) > 1:
                return result[0].data
        return []

def basic_login():
    """basic example to perform login"""
    if not os.path.exists('.hxauth'):
        with open('.hxauth', 'w') as f:
            str1 = 'api_key = your_key\n' \
                   'api_secret = your_secret\n' \
                   'auth = yuanq4@mcmaster.ca:12yy90Qaz&\n' \
                   'base_url = https://api.hexoskin.com\n'
            f.write(str1)

    try:
        with open('.hxauth', 'r') as f:
            conf = dict(map(str.strip, l.split('=', 1)) for l in f.readlines() if l and not l.startswith('#'))
    except:
        raise IOError('Unable to parse .hxauth file! Please verify that the syntax is correct.')

    if conf['api_key'] == 'your_key':
        raise ValueError('Please fill the file: ".hxauth" with credentials')

    try:
        # try an oauth2 login
        auth = conf.pop('auth')
        username, password = auth.split(':')
        api = hexoskin.client.HexoApi(**conf)
        api.oauth2_get_access_token(username, password)
    except hexoskin.errors.HttpBadRequest as e:
        # HexoAuth login
        api = hexoskin.client.HexoApi(auth=auth, **conf)
    return api




api = basic_login()


def stream_and_store_data():
    """Stream all data and store it locally."""
    user = api.account.list()[0]
    datatypes = api.datatype.list()
    datatype_ids = [datatype.id for datatype in datatypes]
    
    poller = DataPoller(api, datatype_ids, user=user.resource_uri)

    filename = f"hexoskin_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['timestamp'] + [f'datatype_{datatype.id}' for datatype in datatypes])

        try:
            while True:
                data = poller.poll()
                if data:
                    for timestamp, values in data.items():
                        row = [datetime.datetime.fromtimestamp(timestamp / api.freq).isoformat()] + values
                        writer.writerow(row)
                        print(f"Data at {timestamp}: {values}")
                time.sleep(1)  # Polling interval
        except KeyboardInterrupt:
            print("Stopping data streaming...")
        except Exception as e:
            print(f"Error while streaming data: {e}")


if __name__ == '__main__':
    stream_and_store_data()
