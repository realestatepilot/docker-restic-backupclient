#!/usr/bin/env python3

import logging as log
import requests
from requests.utils import requote_uri
import os.path
import subprocess
import re

SQLCMDPATH='/opt/mssql-tools/bin/sqlcmd'

def mssql_list_database(host,port,username,password):

	try:
		log.info('Getting list of databases')

		output=subprocess.check_output([
				SQLCMDPATH,
				'-l','2',
				'-S','%s,%s'%(host,port),
				'-U',username,
				'-Q','SELECT name FROM sys.databases;'
			],
			env={'SQLCMDPASSWORD': password}
			).decode()
		log.debug(output)

	except subprocess.CalledProcessError as e:

		log.error('MSSQL list databases failed.')
		return None

	result=[]

	for i,v in enumerate(output.split('\n')):
		if i<2 or v.startswith(" ") or v.startswith("(") or v.strip()=="":
			continue
		result.append(v.strip())

	if len(result)==0:
		log.warn("No databases found!")
		return False

	return result

def mssql_dump_with_config(target_dir,config):
	if not 'host' in config:
		log.error('Missing mysql config: host')
	if not 'username' in config:
		log.error('Missing mysql config: username')
	if not 'password' in config:
		log.error('Missing mysql config: password')
	host=config['host']
	username=config['username']
	password=config['password']
	port=config['port'] if 'port' in config else 1433
	include_patterns=config['include'] if 'include' in config else None
	exclude_patterns=config['exclude'] if 'exclude' in config else None
	return mssql_dump(target_dir,host,port,username,password,include_patterns,exclude_patterns)

def mssql_dump(target_dir,host,port,username,password,include_patterns,exclude_patterns):
	if include_patterns and exclude_patterns:
		log.error("Either inclusion or exclusion of indices is allowed, not both!")
	databases=mssql_list_database(host,port,username,password)
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
				log.info('MSSQL: database %s is included for this dump.'%database)
			else:
				log.info('MSSQL: database %s is not included for this dump.'%database)
				continue
		if exclude_patterns:
			excluded=False
			for p in exclude_patterns:
				if (re.compile(p).match(database)):
					excluded=True
					break
			if excluded:
				log.info('MSSQL: database %s is excluded for this dump.'%database)
				continue
			else:
				log.info('MSSQL: database %s is not excluded for this dump.'%database)
		try:

			log.info('MSSQL: Backup database statements for %s'%(database))
			# hard coded backup dir on mssql server -> mount this outside sql server container
			target_file=os.path.join(os.path.sep,"backup",'%s.bak'%(database))

			sql_cmd="""USE %s;
				GO
				BACKUP DATABASE %s
				TO DISK = '%s'
					WITH FORMAT,
							MEDIANAME = 'SQLServerBackups',
							NAME = 'Full Backup of SQLTestDB';
				GO
			"""%(database, database, target_file)
			log.debug('MSSQL: Backup database statements for %s'%(sql_cmd))

			output=subprocess.check_output([
				SQLCMDPATH,
				'-S','%s,%s'%(host,port),
				'-l','2',
				'-U',username,
				'-Q',sql_cmd
				],
				env={'SQLCMDPASSWORD': password}
				).decode()
			log.info(output)
		except subprocess.CalledProcessError as e:
			log.error('MSSQL Dump failed.')
			return False
	return True


def main():
	log.basicConfig(level=log.INFO,format='%(asctime)s %(levelname)7s: %(message)s')
	import argparse
	parser = argparse.ArgumentParser(description='Dump mssql databases.')
	parser.add_argument('target_dir', metavar='target-dir', type=str,
		help='Directory to dump to')
	parser.add_argument('--host', metavar='host', type=str, help='MSSQL host', required=True)
	parser.add_argument('--port', metavar='host', type=int, help='MSSQL port', default=1433)
	parser.add_argument('-u','--username', metavar='username', type=str, help='MSSQL username', required=True)
	parser.add_argument('-p','--password', metavar='password', type=str, help='MSSQL password', required=True)
	parser.add_argument('-i','--include', metavar='expression', type=str, nargs='*',
		help='Databases to include (regular expression)')
	parser.add_argument('-e','--exclude', metavar='expression', type=str, nargs='*',
		help='Databases to exclude (regular expression)')
	args=parser.parse_args()
	if not os.path.isdir(args.target_dir):
		print('No such directory: %s'%args.target_dir)
		quit(1)

	ok=mssql_list_database(args.host,args.port,args.username,args.password)

	ok=mssql_dump(args.target_dir,args.host,args.port,args.username,args.password,args.include,args.exclude)
	if ok:
		print('Dump successfully created.')
	else:
		print('Dump failed.')
		quit(1)


if __name__ == '__main__':
	log.basicConfig(level=log.INFO,format='%(asctime)s %(levelname)7s: %(message)s')
	main()
