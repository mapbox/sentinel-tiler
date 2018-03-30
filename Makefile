
SHELL = /bin/bash

all: build package


all-custom: build-custom package


build:
	docker build -f ./Dockerfiles/Simple -t lambda:tiler .


build-custom:
	docker build -f ./Dockerfiles/Custom -t lambda:tiler .


package:
	docker run \
		-w /var/task/ \
		--name lambda \
		-itd \
		lambda:tiler
	docker cp lambda:/tmp/package.zip package.zip
	docker stop lambda
	docker rm lambda


#Local Test
test:
	docker run \
		-w /var/task/ \
		--name lambda \
		--env AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
		--env AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
		--env AWS_REGION=eu-central-1 \
		--env PYTHONPATH=/var/task \
		--env GDAL_CACHEMAX=75% \
		--env GDAL_DISABLE_READDIR_ON_OPEN=TRUE \
		--env GDAL_TIFF_OVR_BLOCKSIZE=512 \
		--env VSI_CACHE=TRUE \
		--env VSI_CACHE_SIZE=536870912 \
		-itd \
		lambda:tiler
	docker exec -it lambda bash -c 'unzip -q /tmp/package.zip -d /var/task'
	docker exec -it lambda bash -c 'pip3 install boto3 jmespath python-dateutil -t /var/task'
	docker exec -it lambda python3 -c 'from app.sentinel import APP; print(APP({"path": "/sentinel/bounds/S2A_tile_20161202_16SDG_0", "queryStringParameters": {}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker exec -it lambda python3 -c 'from app.sentinel import APP; print(APP({"path": "/sentinel/metadata/S2A_tile_20161202_16SDG_0", "queryStringParameters": {"pmin":"2", "pmax":"99.8"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker exec -it lambda python3 -c 'from app.sentinel import APP; print(APP({"path": "/sentinel/tiles/S2A_tile_20161202_16SDG_0/10/262/397.png", "queryStringParameters": {"rgb":"04,03,02", "histo":"256,1701-496,1498-798,1449"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker stop lambda
	docker rm lambda


#Local Test
test-custom:
	docker run \
		-w /var/task/ \
		--name lambda \
		--env AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
		--env AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
		--env AWS_REGION=eu-central-1 \
		--env PYTHONPATH=/var/task \
		--env GDAL_DATA=/var/task/share/gdal \
		--env GDAL_CACHEMAX=75% \
		--env GDAL_DISABLE_READDIR_ON_OPEN=TRUE \
		--env GDAL_TIFF_OVR_BLOCKSIZE=512 \
		--env VSI_CACHE=TRUE \
		--env VSI_CACHE_SIZE=536870912 \
		-itd \
		lambda:tiler
	docker exec -it lambda bash -c 'unzip -q /tmp/package.zip -d /var/task'
	docker exec -it lambda bash -c 'pip3 install boto3 jmespath python-dateutil -t /var/task'
	docker exec -it lambda python3 -c 'from app.sentinel import APP; print(APP({"path": "/sentinel/bounds/S2A_tile_20161202_16SDG_0", "queryStringParameters": {"pmin":"2", "pmax":"99.8"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker exec -it lambda python3 -c 'from app.sentinel import APP; print(APP({"path": "/sentinel/metadata/S2A_tile_20161202_16SDG_0", "queryStringParameters": {"pmin":"2", "pmax":"99.8"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker exec -it lambda python3 -c 'from app.sentinel import APP; print(APP({"path": "/sentinel/tiles/S2A_tile_20161202_16SDG_0/10/262/397.png", "queryStringParameters": {"rgb":"04,03,02", "histo":"256,1701-496,1498-798,1449"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker stop lambda
	docker rm lambda


deploy:
	sls deploy
