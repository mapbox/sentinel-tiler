# sentinel-tiler
Create a serverless tile server for Amazon's Sentinel-2 Public Dataset based on rasterio python library.


#### Sentinel data on AWS

Since 2016 ESA Sentinel-2 data is hosted on AWS and can be freely accessed.

> Each file is its own object in the sentinel-s2-l1c Amazon S3 bucket. The data are organised into tiles using the Military grid system. The basic data format is the following:

more info: https://aws.amazon.com/public-datasets/sentinel-2/


# Custom or Simple
Sentinel-2 data are stored in JPEG2000 format. While this has some advantage (mainly file size), this format is not really cloud friendly [ref](https://trac.osgeo.org/gdal/wiki/CloudOptimizedGeoTIFF). JPEG2000 started as a proprietary format but recently there has been a massive work by `University of Louvain` and also `Even Rouault` to develop an open source driver to decode and encode JPEG2000 files.

Quote form `OpenJPEG` [repo](https://github.com/uclouvain/openjpeg)
>OpenJPEG is an open-source JPEG 2000 codec written in C language. It has been developed in order to promote the use of JPEG 2000, a still-image compression standard from the Joint Photographic Experts Group (JPEG). Since April 2015, it is officially recognized by ISO/IEC and ITU-T as a JPEG 2000 Reference Software.

To create the lambda package we need to have GDAL and our python module compiled on a Amazonlinux like machine. Using Docker we can do everything locally ([perrygeo blog](http://www.perrygeo.com/running-python-with-compiled-code-on-aws-lambda.html)) but to keep everything simple and fast we can use the already created **Remotepixel**'s amazonlinux docker image available on [Docker Hub](https://hub.docker.com/r/remotepixel/amazonlinux-gdal/). This docker image has a custom version of GDAL2 compiled supporting GeoTIFF and OpenJPEG formats.

That said, OpenJPEG driver is not yet as fast as the other proprietary Jpeg2000 drivers like ECW, MrSID or Kakadu. In this repo you can have the possibility to create the a custom GDAL install with any of the drivers you have the license for.

Update: Even Rouault has made some major improvements in OpenJPEG 2.3.0 [blog](https://erouault.blogspot.ca/2017/10/optimizing-jpeg2000-decoding.html).

# Installation

##### Requirement
  - AWS Account
  - Docker
  - node + npm


## Create package

##### Simple (using remotepixel/amazonlinux-gdal:latest)

```bash
# Build Amazon linux AMI docker container + Install Python modules + create package
git clone https://github.com/mapbox/sentinel-tiler.git
cd sentinel-tiler/
make all
```

##### Custom

1. Edit `./Dockerfiles/Custom`

2. Create the package:

```bash
# Build Amazon linux AMI docker container + Install Python modules + create package
git clone https://github.com/mapbox/sentinel-tiler.git
cd sentinel-tiler/
make all-custom
```

## Deploy

```bash
#configure serverless (https://serverless.com/framework/docs/providers/aws/guide/credentials/)
npm install
sls deploy
```

:tada: You should be all set there.

---
# Use it: Sentinel-viewer

#### sentinel-tiler + Mapbox GL + Satellite API

The `viewer/` directory contains a UI example to use with your new Lambda Sentinel tiler endpoint. It combine the power of mapbox-gl and the nice developmentseed [sat-api](https://github.com/sat-utils/sat-api) to create a simple and fast **Sentinel-viewer**.


To be able to run it, edit those [two lines](https://github.com/mapbox/sentinel-tiler/blob/master/viewer/js/app.js#L3-L4) in `viewer/js/app.js`
```js
// viewer/js/app.js
3  mapboxgl.accessToken = '{YOUR-MAPBOX-TOKEN}';
4  const sentinel_tiler_url = "{YOUR-API-GATEWAY-URL}";
```

---
## Workflow

1. One AWS ƛ call to get min/max percent cut value for all the bands and bounds

  *Path:* **/sentinel/metdata/{sentinel scene id}**

  *Inputs:*

  - sceneid: Sentinel scene id (`S2{A|B}_tile_{YYYYMMDD}_{utm_zone}{latitude_band}{grid_square}_{img_number}`)

  *Options:*

  - pmin: Histogram cut minimum value in percent (default: 2)  
  - pmax: Histogram cut maximum value in percent (default: 98)  

  *Output:* (dict)

  - bounds: (minX, minY, maxX, maxY) (list)
  - sceneid: scene id (string)
  - rgbMinMax: Min/Max DN values for the linear rescaling (dict)

  *Example:* `<api-gateway-url>/sentinel/metadata/S2A_tile_20161202_16SDG_0?pmin=5&pmax=95`

2. Parallel AWS ƛ calls (one per mercator tile) to retrieve corresponding Sentinel data

  *Path:* **/sentinel/tiles/{sentinel scene id}/{z}/{x}/{y}.{ext}**

  *Inputs:*

  - sceneid: Sentinel scene id (`S2{A|B}_tile_{YYYYMMDD}_{utm_zone}{latitude_band}{grid_square}_{img_number}`)
  - x: Mercator tile X index
  - y: Mercator tile Y index
  - z: Mercator tile ZOOM level
  - ext: Image format to return ("jpg" or "png")

  *Options:*

  - rgb: Bands index for the RGB combination (default: (04, 03, 02))
  - r_bds: First band (red) DN min and max values (default: (0, 16000))
  - g_bds: Second band (green) DN min and max values (default: (0, 16000))
  - b_bds: Third band (blue) DN min and max values (default: (0, 16000))
  - tile: Output image size (default: 256)

  *Output:*

  - base64 encoded image PNG or JPEG (string)

  *Example:*
  - `<api-gateway-url>/sentinel/tile/S2A_tile_20161202_16SDG_0/10/262/397.png`
  - `<api-gateway-url>/sentinel/tile/S2A_tile_20161202_16SDG_0/10/262/397.png?rgb=04,03,02&r_bds=100,3000&g_bds=130,2700&b_bds=500,4500&tile=512`


---

#### Infos & links
- [rio-tiler](https://github.com/mapbox/rio-tiler) rasterio plugin that process Sentinel data hosted on AWS S3.
- [Introducing the AWS Lambda Tiler](https://hi.stamen.com/stamen-aws-lambda-tiler-blog-post-76fc1138a145)
- Humanitarian OpenStreetMap Team [oam-dynamic-tiler](https://github.com/hotosm/oam-dynamic-tiler)
