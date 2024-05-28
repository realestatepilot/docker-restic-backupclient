#!/usr/bin/env python3

import logging as log
import os.path
import subprocess

def mongodump_with_config(target_dir,config):
	if 'host' not in config:
		log.error('Missing mongodump config: host')
	if 'username' not in config:
		log.error('Missing mongodump config: username')
	if 'password' not in config:
		log.error('Missing mongodump config: password')
	host=config['host']
	username=config['username']
	password=config['password']
	port=config['port'] if 'port' in config else 27017
	dump_version=config['dump_version'] if 'dump_version' in config else 3
	return mongodump(target_dir,host,port,username,password,dump_version)

def mongodump(target_dir,host,port,username,password,dump_version):
	log.info('Setting binary.')
	if dump_version == 3:
		binary = "mongodump"
	elif dump_version == 4:
		binary = "mongodump_rc"
	else:
		log.error('Couldnt set binary.')
		return False

	try:
		log.info('Dumping mongodb at %s'%host)
		subprocess.run("".join([
			'nice -n 19 '
			'ionice -c3 '
			'%s '%binary,
			'--host=%s '%host,
			'--port=%s '%port,
			'--username=%s '%username,
			'--password=%s '%password,
			'--forceTableScan ',
			'-o %s '%target_dir
		]),shell=True,check=True)
	except subprocess.CalledProcessError:
		log.error('Mongodump failed.')
		return False
	return True

def main():
	log.basicConfig(level=log.INFO,format='%(asctime)s %(levelname)7s: %(message)s')
	import argparse
	parser = argparse.ArgumentParser(description='Dump mongo databases.')
	parser.add_argument('target_dir', metavar='target-dir', type=str,
		help='Directory to dump to')
	parser.add_argument('--host', metavar='host', type=str, help='Mongodb host', required=True)
	parser.add_argument('--port', metavar='host', type=int, help='Mongodb port', default=27017)
	parser.add_argument('-u','--username', metavar='username', type=str, help='Mongodb username', required=True)
	parser.add_argument('-p','--password', metavar='password', type=str, help='Mongodb password', required=True)
	parser.add_argument('--dump_version', metavar='3 or 4', type=int, help='Choose between mongodump version 3.x.x and 4.x.x. Implemented to avoid failing dumps due to version mismatch. Default 3.', default=3)
	args=parser.parse_args()
	if not os.path.isdir(args.target_dir):
		print('No such directory: %s'%args.target_dir)
		quit(1)

	ok=mongodump(args.target_dir,args.host,args.port,args.username,args.password,args.dump_version)
	if ok:
		print('Dump successfully created.')
	else:
		print('Dump failed.')
		quit(1)



if __name__ == '__main__':
	main()
