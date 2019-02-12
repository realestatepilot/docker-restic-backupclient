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

	log.info('Starting backup')
	try:
		subprocess.check_call([
			'restic',
			'backup',
			'--hostname',get_env('RESTIC_HOSTNAME'),
			backup_root
			],stderr=subprocess.STDOUT)
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
	get_env('RESTIC_HOSTNAME')
	get_env('BACKUP_ROOT')

	if args.cmd=='run':
		result=run_backup()
		if not result:
			quit(1)
	else:
		schedule_backup(args.cronexpression)


if __name__ == '__main__':
	main()
