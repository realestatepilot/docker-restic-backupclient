# Change Log

## 0.8.1 
* Versionierung an die Version des Restic-Containers angepasst

## 0.3.4 
* OOM bei großem Backup mit 6GB RAM - env variable `GOGC=20` hilft

## 0.3.3

* dynamic provisioned volumes for cacheDir und restore volume
* remove default resource limits

## 0.3.2

* secret get dynamic naming to allow multiple instances in one namespace

## 0.3.1

* ???

## 0.3.0

* Dump Only Modus

## 0.2.1
* probes at restic monitor errors to fast, sensibility reduced

## 0.2.0
Breaking Change
* set default ressource requests

New
* Support exsisting  persistent volume claims
* remove some line breaks in deployment
* use image 0.7.1
* values.yaml for testing
