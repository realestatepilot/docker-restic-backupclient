#!/usr/bin/env python3

from os import environ
import logging as log
import argparse
from crontab import CronTab
from datetime import datetime,timedelta
import time
import subprocess
import os.path
import yaml
import shutil
import elasticdump
import mysqldump
import mongodump

def fail(msg,args):
	log.error(msg,args)
	quit(1)

UNDEFINED=object()
def get_env(name,default=UNDEFINED):
	if name in environ:
		return environ[name]
	if default != UNDEFINED:
		return default

	fail('Please set the environment variable %s',name)

class ParseCronExpressions(argparse.Action):
	def __init__(self, option_strings, dest, **kwargs):
		super(ParseCronExpressions, self).__init__(option_strings, dest, **kwargs)

	def __call__(self, parser, namespace, values, option_string=None):
		items=[]
		for value in values:
			try:
				items.append(CronTab(value))
			except ValueError as e:
				raise argparse.ArgumentError(self,'%s: %s'%(value,e))

		setattr(namespace, self.dest, items)

def get_next_schedule(crontab):
	now=datetime.now()
	delay=-1
	for cron in crontab:
		cron_delay=cron.next(now,default_utc=False)
		if delay<0 or cron_delay<delay:
			delay=cron_delay
	return now+timedelta(seconds=delay)

def load_config():
	config_file=get_env('BACKUP_CONFIG',None)
	if config_file is None:
		return {}
	if not os.path.exists(config_file):
		log.error('Config does not exist: %s'%config_file)
	try:
		log.info('Using extra config from %s'%config_file)
		with open(config_file,'r') as config:
			return yaml.load(config)
	except:
		log.exception('Unable to read config file %s'%config_file)
		return None

def run_pre_backup_script(scriptinfo):
	if type(scriptinfo) is not dict:
		log.error("Expected pre-backup-script to be a dict, got: %s",type(scriptinfo).__name__)
		return False
	if not 'script' in scriptinfo:
		log.error("Pre-backup-script does not contain a 'script' property.")
		return False

	script=scriptinfo['script']
	fail_on_error=bool(scriptinfo['fail-on-error']) if 'fail-on-error' in scriptinfo else True
	description=("Executing pre-backup-script: %s"%scriptinfo['description']) if 'description' in scriptinfo else "Executing pre-backup-script"

	log.info(description)
	try:
		subprocess.check_call(script,stderr=subprocess.STDOUT,shell=True)
		log.info("Pre-backup-script succeeded")
	except subprocess.CalledProcessError as e:
		if (fail_on_error):
			log.error("Pre-backup-script failed: %s",e)
			return False
		log.warning("Pre-backup-script failed: %s",e)

	return True


def run_backup():
	backup_root=get_env('BACKUP_ROOT')
	log.info('Initializing repository')
	try:
		subprocess.check_output([
			'restic',
			'init'
			],stderr=subprocess.STDOUT)
		log.info('Repository initialized.')
	except subprocess.CalledProcessError as e:
		output=e.output.decode()
		if 'repository master key and config already initialized' in output or 'config file already exists' in output:
			log.info('Repository was already initialized.')
		else:
			log.error('Initializing repository failed: %s'%output)
			return False

	config=load_config()
	if config is None:
		return False

	if 'pre-backup-scripts' in config:
		for script in config['pre-backup-scripts']:
			if not run_pre_backup_script(script):
				log.error('Stopped due to pre-backup script failures')
				return False

	if 'elasticdump' in config:
		elasticdump_dir=os.path.join(backup_root,'elasticdump')
		try:
			shutil.rmtree(elasticdump_dir)
		except:
			pass
		if os.path.exists(elasticdump_dir):
			log.error('Unable to delete old elasticdump dir at %s'%elasticdump_dir)
		os.mkdir(elasticdump_dir)

		log.info('Running elasticdump to %s'%elasticdump_dir)
		elasticdump_ok=elasticdump.es_dump_with_config(elasticdump_dir,config['elasticdump'])
		if not elasticdump_ok:
			log.error('Elasticdump failed. Backup canceled.')
			return False

	if 'mysqldump' in config:
		mysqldump_dir=os.path.join(backup_root,'mysqldump')
		try:
			shutil.rmtree(mysqldump_dir)
		except:
			pass
		if os.path.exists(mysqldump_dir):
			log.error('Unable to delete old mysqldump dir at %s'%mysqldump_dir)
		os.mkdir(mysqldump_dir)

		log.info('Running mysqldump to %s'%mysqldump_dir)
		mysqldump_ok=mysqldump.mysql_dump_with_config(mysqldump_dir,config['mysqldump'])
		if not mysqldump_ok:
			log.error('Mysqldump failed. Backup canceled.')
			return False

	if 'mongodump' in config:
		mongodump_dir=os.path.join(backup_root,'mongodump')
		try:
			shutil.rmtree(mongodump_dir)
		except:
			pass
		if os.path.exists(mongodump_dir):
			log.error('Unable to delete old mongodump dir at %s'%mongodump_dir)
		os.mkdir(mongodump_dir)

		log.info('Running mongodump to %s'%mongodump_dir)
		mongodump_ok=mongodump.mongodump_with_config(mongodump_dir,config['mongodump'])
		if not mongodump_ok:
			log.error('Mongodump failed. Backup canceled.')
			return False

	cmd=[
		'nice','-n19',
		'ionice','-c3',
		'restic',
		'backup',
		'--host',get_env('BACKUP_HOSTNAME'),
	]

	# exclude caches (http://bford.info/cachedir/spec.html)
	if not ('exclude-caches' in config and bool(config['exclude-caches'])):
		cmd.append('--exclude-caches')

	# exclude other files
	if 'exclude' in config:
		excludes=config['exclude']
		if type(excludes) is not list:
			excludes=[excludes]
		for exclude in excludes:
			log.info("Excluding: %s"%exclude)
		cmd.append('--exclude')
		cmd.append(exclude)

	cmd.append(backup_root)

	log.info('Starting backup')
	try:
		subprocess.check_call(cmd,stderr=subprocess.STDOUT)
		
		log.info('Backup finished.')
	except subprocess.CalledProcessError as e:
			log.info('Backup failed.')
			return False

	if 'keep' in config:
		keep=config['keep']
		cleanup_command=[
			'restic',
			'forget',
			'--prune'
		]
		keep_is_valid=False
		for keep_type in ['last','hourly','daily','weekly','monthly','yearly']:
			if keep_type in keep:
				keep_is_valid=True
				cleanup_command+=['--keep-%s'%keep_type,str(keep[keep_type])]
		if not keep_is_valid:
			log.warn('Keep configuration is invalid - not deleting old backups.')
		else:
			log.info('Unlocking repository')
			subprocess.check_call(['restic','unlock'],stderr=subprocess.STDOUT)
			log.info('Deleting old backups')
			try:
				subprocess.check_call(cleanup_command,stderr=subprocess.STDOUT)
				log.info('Backup finished.')
			except subprocess.CalledProcessError as e:
				log.warn('Cleanup failed!')


def schedule_backup(crontab):
	while True:
		next_schedule=get_next_schedule(crontab)
		log.info('Scheduling next backup at %s'%next_schedule)
		while True:
			now=datetime.now()
			if now>=next_schedule:
				break
			time.sleep(10)
		try:
			run_backup()
		except:
			log.exception("Something went unexpectedly wrong!")

def main():
	log.basicConfig(level=log.INFO,format='%(asctime)s %(levelname)7s: %(message)s')
	parser = argparse.ArgumentParser(description='Perform backups with restic')
	subparsers = parser.add_subparsers(help='sub-command help',dest='cmd')
	subparsers.required = True
	parser_run = subparsers.add_parser('run', help='Run a backup now.')
	parser_schedule = subparsers.add_parser('schedule', help='Schedule backups.')
	parser_schedule.add_argument('cronexpression',nargs='+',action=ParseCronExpressions,
		help='Time to schedule the backup (cron expression, see https://pypi.org/project/crontab/)')

	args=parser.parse_args()

	get_env('RESTIC_REPOSITORY')
	get_env('RESTIC_PASSWORD')
	get_env('BACKUP_HOSTNAME')
	get_env('BACKUP_ROOT')

	if args.cmd=='run':
		result=run_backup()
		if not result:
			quit(1)
	else:
		schedule_backup(args.cronexpression)


if __name__ == '__main__':
	main()
