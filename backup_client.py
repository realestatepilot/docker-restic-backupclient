#!/usr/bin/env python3

from os import environ
import logging as log
import argparse
from crontab import CronTab
from datetime import datetime,timedelta
import time
import subprocess
import os.path
import re
import gc
import yaml
import shutil
import elasticdump
import mysqldump
import pgdump
import mongodump

def fail(msg,args):
	log.error(msg,args)
	quit(1)

def resolve_env_placeholders(template):
	resolveDepth = 0
	while resolveDepth < 10:
		resolveDepth += 1
		changed = False
		for placeholder, key in re.findall('(\$\(([a-zA-Z0-9_-]+)\))', template):
			if key in environ:
				template = template.replace(placeholder, environ[key])
				changed = True
		if not changed:
			break
	return template

UNDEFINED=object()
def get_env(name,default=UNDEFINED):
	if name in environ:
		return resolve_env_placeholders(environ[name])
	if default != UNDEFINED:
		return default

	fail('Please set the environment variable %s',name)

class ParseCronExpressions(argparse.Action):
	def __init__(self, option_strings, dest, **kwargs):
		super(ParseCronExpressions, self).__init__(option_strings, dest, **kwargs)

	def __call__(self, parser, namespace, values, option_string=None):
		items=[]
		if type(values) is str:
			values=[values]
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
			return yaml.safe_load(config)
	except:
		log.exception('Unable to read config file %s'%config_file)
		return None

def run_pre_backup_script(scriptinfo):
	if type(scriptinfo) is not dict:
		log.error("Expected pre-backup-script to be a dict, got: %s",type(scriptinfo).__name__)
		return False
	if 'script' not in scriptinfo:
		log.error("Pre-backup-script does not contain a 'script' property.")
		return False

	script=scriptinfo['script']
	fail_on_error=bool(scriptinfo['fail-on-error']) if 'fail-on-error' in scriptinfo else True
	description=("Executing pre-backup-script: %s"%scriptinfo['description']) if 'description' in scriptinfo else "Executing pre-backup-script"

	log.info(description)
	try:
		subprocess.run(script,stderr=subprocess.STDOUT,shell=True,check=True)
		log.info("Pre-backup-script succeeded")
	except subprocess.CalledProcessError as e:
		if (fail_on_error):
			log.error("Pre-backup-script failed: %s",e)
			return False
		log.warning("Pre-backup-script failed: %s",e)

	return True

def init_restic_repo():
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

def run_backup(prune=False):
	backup_root=get_env('BACKUP_ROOT')
	init_restic_repo()

	log.info('Unlocking repository')
	subprocess.run(['restic','unlock'],stderr=subprocess.STDOUT,check=True)

	config=load_config()
	if config is None:
		return False

	if not (os.path.exists(backup_root)):
		log.info('Backup mount point not found %s. Creating internal mount point for dump jobs. This might be ok if you only backup database dumps.'%backup_root)
		os.mkdir(backup_root)

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

	if 'pgdump' in config:
		pgdump_dir=os.path.join(backup_root,'pgdump')
		try:
			shutil.rmtree(pgdump_dir)
		except:
			pass
		if os.path.exists(pgdump_dir):
			log.error('Unable to delete old pgdump dir at %s'%pgdump_dir)
		os.mkdir(pgdump_dir)

		log.info('Running pgdump to %s'%pgdump_dir)
		pgdump_ok=pgdump.pg_dump_with_config(pgdump_dir,config['pgdump'])
		if not pgdump_ok:
			log.error('Pgdump failed. Backup canceled.')
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

	# ignore inode for changed-file checks (default is true)
	if not ('ignore-inode' in config and bool(config['ignore-inode'])):
		cmd.append('--ignore-inode')

	# set cacheDir if not default one should be used
	if ('cache-dir' in config ):
		log.info("cache-dir is: "+config['cache-dir'])
		cmd.append('--cache-dir')
		cmd.append(config['cache-dir'])

    # dont use restic caching
	if ('no-cache' in config ):
		log.info("not using cache")
		cmd.append(f"--no-cache={config['no-cache']}")

	# include files to backupset from given files
	if 'include-from' in config:
		includes=config['include-from']
		if type(includes) is not list:
				includes=[includes]
		for include in includes:
			log.info("Use include from: %s"%include)
			cmd.append('--files-from')
			cmd.append(include)

	# exclude other files
	if 'exclude' in config:
		excludes=config['exclude']
		if type(excludes) is not list:
			excludes=[excludes]
		for exclude in excludes:
			log.info("Excluding: %s"%exclude)
			cmd.append('--exclude')
			cmd.append(exclude)

	# if include is set no backuproot should given as argument
	if 'include-from' not in config:
		cmd.append(backup_root)

	log.info('Starting backup')
	try:
		subprocess.run(cmd,stderr=subprocess.STDOUT,check=True)
		
		log.info('Backup finished.')
	except subprocess.CalledProcessError:
		log.info('Backup failed.')
		return False

	if not clean_old_backups(config):
		return False

	if prune:
		return prune_repository()

	return True

def clean_old_backups(config=None):

	if config is None:
		# direct call, init first
		config=load_config()
		init_restic_repo()

	if config is None:
		return False

	cleanup_command=[
		'restic',
		'forget',
	]

	if 'keep' in config:
		keep=config['keep']
		keep_is_valid=False
		for keep_type in ['last','hourly','daily','weekly','monthly','yearly']:
			if keep_type in keep:
				keep_is_valid=True
				cleanup_command+=['--keep-%s'%keep_type,str(keep[keep_type])]
		if not keep_is_valid:
			log.warning('Keep configuration is invalid - not deleting old backups.')
			return
	else:
		keep_is_valid=False
		for keep_type in ['last','hourly','daily','weekly','monthly','yearly']:
			keep_env='KEEP_%s' % (keep_type.upper())
			if keep_env in environ:
				keep_is_valid=True
				cleanup_command+=['--keep-%s'%keep_type,str(environ[keep_env])]
		if not keep_is_valid:
			log.warning('Rotation not configured. Keeping backups forever.')
			return

	log.info('Unlocking repository')
	subprocess.run(['restic','unlock'],stderr=subprocess.STDOUT,check=True)
	log.info('Deleting old backups')
	try:
		subprocess.run(cleanup_command,stderr=subprocess.STDOUT,check=True)
		log.info('Cleanup finished.')
	except subprocess.CalledProcessError:
		log.warning('Cleanup failed!')
		return False

	return True

def get_prune_timeout():
	prune_timeout=get_env('RESTIC_PRUNE_TIMEOUT',UNDEFINED)
	if (prune_timeout is None):
		return None

	# https://stackoverflow.com/a/4628148/1471588
	regex = re.compile(r'^((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?$')
	parts = regex.match(prune_timeout)
	if not parts:
		fail('Invalid RESTIC_PRUNE_TIMEOUT: %s',prune_timeout)
		return None
	parts = parts.groupdict()
	time_params = {}
	for name, param in parts.items():
		if param:
			time_params[name] = int(param)
	prune_timeout=timedelta(**time_params)
	if prune_timeout.total_seconds()<=0:
		return None
	return prune_timeout

def prune_repository(config=None):
	if config is None:
		# direct call, init first
		config=load_config()
		init_restic_repo()

	if config is None:
		return False

	prune_timeout=get_prune_timeout()

	prune_command=[
		'restic',
		'prune',
		'-o','s3.list-objects-v1=true'  # See https://github.com/restic/restic/issues/3761
	]

	log.info('Unlocking repository')
	subprocess.run(['restic','unlock'],stderr=subprocess.STDOUT,check=True)

	if prune_timeout is None:
		log.info('Pruning repository')
	else:
		log.info('Pruning repository (timeout %s)'%get_env('RESTIC_PRUNE_TIMEOUT'))
		prune_command=['timeout',str(prune_timeout.total_seconds())] + prune_command
	try:
		subprocess.run(prune_command,stderr=subprocess.STDOUT,check=True)
		log.info('Prune finished.')
	except subprocess.CalledProcessError:
		log.warning('Prune failed!')
		return False

	return True


def schedule_backup(crontab,prunecron=None):
	next_is_prune=False
	while True:
		next_schedule=get_next_schedule(crontab)
		next_is_prune=False

		if prunecron is not None:
			next_prune=get_next_schedule(prunecron)
			if next_prune < next_schedule:
				next_schedule = next_prune
				next_is_prune = True

		if next_is_prune:
			log.info('Scheduling next prune at %s'%next_schedule)
		else:
			log.info('Scheduling next backup at %s'%next_schedule)
		while True:
			now=datetime.now()
			if now>=next_schedule:
				break
			time.sleep(10)
		try:
			if next_is_prune:
				prune_repository()
			else:
				run_backup(prunecron is None)
		except:
			log.exception("Something went unexpectedly wrong!")
		finally:
			gc.collect()


def main():
	log.basicConfig(level=log.INFO,format='%(asctime)s %(levelname)7s: %(message)s')
	parser = argparse.ArgumentParser(description='Perform backups with restic')
	subparsers = parser.add_subparsers(help='sub-command help',dest='cmd')
	subparsers.required = True
	parser_run = subparsers.add_parser('run', help='Run a backup now and rotate+prune afterwards.')
	parser_run = subparsers.add_parser('rotate', help='Rotate backups now.')
	parser_run = subparsers.add_parser('prune', help='Prune the repository now')
	parser_schedule = subparsers.add_parser('schedule', help='Schedule backups.')
	parser_schedule.add_argument('--prune',dest='prunecron',action=ParseCronExpressions,
		help='Time to prune the backup (cron expression, see https://pypi.org/project/crontab/)')
	parser_schedule.add_argument('cronexpression',nargs='+',action=ParseCronExpressions,
		help='Time to schedule the backup (cron expression, see https://pypi.org/project/crontab/)')

	args=parser.parse_args()

	get_env('RESTIC_REPOSITORY')
	get_env('RESTIC_PASSWORD')
	get_env('BACKUP_HOSTNAME')
	get_env('BACKUP_ROOT')
	get_prune_timeout()

	if args.cmd=='run':
		result=run_backup(True)
		if not result:
			quit(1)
	elif args.cmd=='rotate':
		result=clean_old_backups(None)
		if not result:
			quit(1)
	elif args.cmd=='prune':
		result=prune_repository(None)
		if not result:
			quit(1)
	else:
		schedule_backup(args.cronexpression, args.prunecron)


if __name__ == '__main__':
	main()
