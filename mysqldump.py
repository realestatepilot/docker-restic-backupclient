#!/usr/bin/env python3

import logging as log
import requests
from requests.utils import requote_uri
import os.path
import subprocess
import re

def mysql_list_database(host,port,username,password):

	try:
		log.info('Getting list of databases')
		output=subprocess.check_output([
			'mysqlshow',
			'--host=%s'%host,
			'--port=%s'%port,
			'--user=%s'%username,
			'--password=%s'%password
			]).decode()
	except subprocess.CalledProcessError as e:
		log.error('Mysqlshow failed.')
		return None

	result=[]

	for i,v in enumerate(output.split('\n')):
		if i<3 or not v.startswith("| "):
			continue
		v=v.strip('| ')
		if v in ('information_schema','performance_schema'):
			continue
		result.append(v)

	if len(result)==0:
		print("No databases found!")
		return False

	return result

def mysql_dump_with_config(target_dir,config):
	if not 'host' in config:
		log.error('Missing mysql config: host')
	if not 'username' in config:
		log.error('Missing mysql config: username')
	if not 'password' in config:
		log.error('Missing mysql config: password')
	host=config['host']
	username=config['username']
	password=config['password']
	port=config['port'] if 'port' in config else 3306
	include_patterns=config['include'] if 'include' in config else None
	exclude_patterns=config['exclude'] if 'exclude' in config else None
	return mysql_dump(target_dir,host,port,username,password,include_patterns,exclude_patterns)

def mysql_dump(target_dir,host,port,username,password,include_patterns,exclude_patterns):
	if include_patterns and exclude_patterns:
		log.error("Either inclusion or exclusion of indices is allowed, not both!")
	databases=mysql_list_database(host,port,username,password)
	if databases is None:
		return False

	for database in databases:
		if include_patterns:
			included=False
			for p in include_patterns:
				if (re.compile(p).match(database)):
					included=True
					break
			if included:
				log.info('Mysql: database %s is included for this dump.'%database)
			else:
				log.info('Mysql: database %s is not included for this dump.'%database)
				continue
		if exclude_patterns:
			excluded=False
			for p in exclude_patterns:
				if (re.compile(p).match(database)):
					excluded=True
					break
			if excluded:
				log.info('Mysql: database %s is excluded for this dump.'%database)
				continue
			else:
				log.info('Mysql: database %s is not excluded for this dump.'%database)
		try:
			log.info('Mysql: Dumping DROP/CREATE statements for %s'%(database))
			subprocess.check_call("".join([
				'nice -n 19 '
				'ionice -c3 '
				'mysqldump '
				'--host=%s '%host,
				'--port=%s '%port,
				'--user=%s '%username,
				'--password=%s '%password,
				'--single-transaction ',
				'--no-data ',
				'--add-drop-database ',
				'--no-create-info ',
				'--databases %s '%database,
				'| nice -n 19 gzip --best --rsyncable > %s '%os.path.join(target_dir,'MYSQL_%s_DROP_CREATE.sql.gz'%(database))
				]),shell=True)
			log.info('Mysql: Dumping DATA for %s'%(database))
			subprocess.check_call("".join([
				'nice -n 19 '
				'ionice -c3 '
				'mysqldump '
				'--host=%s '%host,
				'--port=%s '%port,
				'--user=%s '%username,
				'--password=%s '%password,
				'--single-transaction ',
				'--no-create-db ',
				database,
				'| nice -n 19 gzip --best --rsyncable > %s '%os.path.join(target_dir,'MYSQL_%s_DATA.sql.gz'%(database))
				]),shell=True)
		except subprocess.CalledProcessError as e:
			log.error('Mysqldump failed.')
			return False
	return True

def main():
	log.basicConfig(level=log.INFO,format='%(asctime)s %(levelname)7s: %(message)s')
	import argparse
	parser = argparse.ArgumentParser(description='Dump mysql databases.')
	parser.add_argument('target_dir', metavar='target-dir', type=str,
		help='Directory to dump to')
	parser.add_argument('--host', metavar='host', type=str, help='MySQL host', required=True)
	parser.add_argument('--port', metavar='host', type=int, help='MySQL port', default=3306)
	parser.add_argument('-u','--username', metavar='username', type=str, help='Mysql username', required=True)
	parser.add_argument('-p','--password', metavar='password', type=str, help='Mysql password', required=True)
	parser.add_argument('-i','--include', metavar='expression', type=str, nargs='*',
		help='Databases to include (regular expression)')
	parser.add_argument('-e','--exclude', metavar='expression', type=str, nargs='*',
		help='Databases to exclude (regular expression)')
	args=parser.parse_args()
	if not os.path.isdir(args.target_dir):
		print('No such directory: %s'%args.target_dir)
		quit(1)

	ok=mysql_dump(args.target_dir,args.host,args.port,args.username,args.password,args.include,args.exclude)
	if ok:
		print('Dump successfully created.')
	else:
		print('Dump failed.')
		quit(1)



if __name__ == '__main__':
	main()
