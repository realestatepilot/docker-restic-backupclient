#!/usr/bin/env python3

import logging as log
import requests
from requests.utils import requote_uri
import os.path
import subprocess

def influxdump_with_config(target_dir,config):
	if not 'host' in config:
		log.error('Missing influxdump config: host')
	host=config['host']
	port=config['port'] if 'port' in config else 8088
	database=config['database'] if 'database' in config else None
	return influxdump(target_dir,host,port,database)

def influxdump(target_dir,host,port,database):
	try:
		log.info('Dumping influxdb at %s'%host)
		subprocess.check_call("".join([
			'nice -n 19 ',
			'ionice -c3 ',
			'influxd ',
			'backup ',
			'--portable ',
			'--host=%s:%s '%(host,port),
			('' if database is None else '--database=%s'%(database)),
			target_dir
			]),shell=True)
	except subprocess.CalledProcessError as e:
		log.error('Influxdump failed.')
		return False
	return True

def main():
	log.basicConfig(level=log.INFO,format='%(asctime)s %(levelname)7s: %(message)s')
	import argparse
	parser = argparse.ArgumentParser(description='Dump influxdb databases.')
	parser.add_argument('target_dir', metavar='target-dir', type=str,
		help='Directory to dump to')
	parser.add_argument('--host', metavar='host', type=str, help='Mongodb host', required=True)
	parser.add_argument('--port', metavar='host', type=int, help='Mongodb port', default=8088)
	parser.add_argument('--database', metavar='database', type=int, help='Dump a single database', default=None)
	args=parser.parse_args()
	if not os.path.isdir(args.target_dir):
		print('No such directory: %s'%args.target_dir)
		quit(1)

	ok=mongodump(args.target_dir,args.host,args.port,args.username,args.password)
	if ok:
		print('Dump successfully created.')
	else:
		print('Dump failed.')
		quit(1)



if __name__ == '__main__':
	main()
