#!/usr/bin/env python3

import logging as log
import requests
from requests.utils import requote_uri
import os.path
import subprocess
import urllib
import re

def es_list_indices(url,username,password):
	if username is not None and password is not None:
		auth=(username,password)
	else:
		auth=None
	response=requests.get('%s/_cat/indices?v&format=json'%url,auth=auth)
	if (response.status_code != 200):
		log.error("Unable to list elasticsearch indices: %s"%response.text)
		return None
	result=[]
	for indexData in response.json():
		result.append(indexData['index'])
	return result

def es_dump_with_config(target_dir,config):
	if not 'url' in config:
		log.error('Missing elasticdump config: url')
	url=config['url']
	username=config['username'] if 'username' in config else None
	password=config['password'] if 'password' in config else None
	include_patterns=config['include'] if 'include' in config else None
	exclude_patterns=config['exclude'] if 'exclude' in config else None
	return es_dump(target_dir,url,username,password,include_patterns,exclude_patterns)

def es_dump(target_dir,url,username,password,include_patterns,exclude_patterns):
	if include_patterns and exclude_patterns:
		log.error("Either inclusion or exclusion of indices is allowed, not both!")
	indices=es_list_indices(url,username,password)
	if indices is None:
		return False
	if username is not None and password is not None:
		urlparts=urllib.parse.urlparse(url)
		url=urlparts._replace(netloc='%s:%s@%s'%(
			username,
			urllib.parse.quote(password),
			urlparts.netloc)).geturl()

	for index in indices:
		if include_patterns:
			included=False
			for p in include_patterns:
				if (re.compile(p).match(index)):
					included=True
					break
			if included:
				log.info('Elasticsearch: index %s is included for this dump.'%index)
			else:
				log.info('Elasticsearch: index %s is not included for this dump.'%index)
				continue
		if exclude_patterns:
			excluded=False
			for p in exclude_patterns:
				if (re.compile(p).match(index)):
					excluded=True
					break
			if excluded:
				log.info('Elasticsearch: index %s is excluded for this dump.'%index)
				continue
			else:
				log.info('Elasticsearch: index %s is not excluded for this dump.'%index)
		try:
			for datatype in ['alias','mapping','data']:
				log.info('Elasticsearch: Dumping %s for %s'%(datatype,index))
				subprocess.check_call([
					'elasticdump',
					'--input','%s/%s'%(url,index),
					'--type',datatype,
					'--output',os.path.join(target_dir,'%s__%s.json'%(index,datatype))
					])
		except subprocess.CalledProcessError as e:
			log.error('Elasticsearch dump failed.')
			return False
	return True

def main():
	log.basicConfig(level=log.INFO,format='%(asctime)s %(levelname)7s: %(message)s')
	import argparse
	parser = argparse.ArgumentParser(description='Dump elasticsearch indices.')
	parser.add_argument('url', metavar='url', type=str, help='URL to elasticsearch')
	parser.add_argument('target_dir', metavar='target-dir', type=str,
		help='Directory to dump to')
	parser.add_argument('-u','--username', metavar='username', type=str, default=None,
		help='Username for basic auth to elasticsearch')
	parser.add_argument('-p','--password', metavar='password', type=str, default=None,
		help='Password for basic auth to elasticsearch')
	parser.add_argument('-i','--include', metavar='expression', type=str, nargs='*',
		help='Indices to include (regular expression)')
	parser.add_argument('-e','--exclude', metavar='expression', type=str, nargs='*',
		help='Indices to exclude (regular expression)')
	args=parser.parse_args()
	if not os.path.isdir(args.target_dir):
		print('No such directory: %s'%args.target_dir)
		quit(1)

	ok=es_dump(args.target_dir,args.url,args.username,args.password,args.include,args.exclude)
	if ok:
		print('Dump successfully created.')
	else:
		print('Dump failed.')
		quit(1)



if __name__ == '__main__':
	main()
