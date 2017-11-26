"use strict";

mapboxgl.accessToken = '{YOUR-MAPBOX-TOKEN}';
const sentinel_tiler_url = '{YOUR-API-GATEWAY-ENDPOINT}'; //e.g https://xxxxxxxxxx.execute-api.xxxxxxx.amazonaws.com/production
const sat_api = 'https://api.developmentseed.org/satellites/?search=';

let scope = {};

////////////////////////////////////////////////////////////////////////////////
const sortScenes = (a, b) => {
    return Date.parse(b.date) - Date.parse(a.date);
};


const buildQueryAndRequestS2 = (features) => {
    $('.list-img').scrollTop(0);
    $('.list-img').empty();
    $('.errorMessage').addClass('none');
    $('.sentinel-info').addClass('none');

    if (map.getSource('sentinel-tiles')) map.removeSource('sentinel-tiles');
    if (map.getLayer('sentinel-tiles')) map.removeLayer('sentinel-tiles');

    const prStr = [].concat.apply([], features.map(function(e){
        return "(grid_square:" +
            e.properties.Name.slice(3, 5) +
            "+AND+latitude_band:" +
            e.properties.Name.slice(2, 3) +
            "+AND+utm_zone:" +
            e.properties.Name.slice(0, 2) +
            ")";
    })).join('+OR+');

    const query = sat_api + 'satellite_name:sentinel-2+AND+(' + prStr + ")&limit=2000";
    const results = [];

    $.getJSON(query, function (data) {
        if (data.meta.found !== 0) {

            for (let i = 0; i < data.results.length; i += 1) {
                let scene = {};
                scene.date = data.results[i].date;
                scene.cloud = data.results[i].cloud_coverage;
                scene.utm_zone = data.results[i].utm_zone.toString();
                scene.grid_square = data.results[i].grid_square;
                scene.coverage = data.results[i].data_coverage_percentage;
                scene.latitude_band = data.results[i].latitude_band;
                scene.sceneID = data.results[i].scene_id;
                scene.browseURL = data.results[i].thumbnail.replace('.jp2', ".jpg");
                scene.path = data.results[i].aws_path.replace('tiles', "#tiles");
                scene.grid = scene.utm_zone + scene.latitude_band + scene.grid_square;
                results.push(scene);
            }

            results.sort(sortScenes);

            for (let i = 0; i < results.length; i += 1) {

                $('.list-img').append(
                    '<div class="list-element" onclick="initScene(\'' + results[i].sceneID + '\',\'' + results[i].date + '\')">' +
                          '<div class="block-info">' +
                              '<img "class="img-item lazy lazyload" src="' + results[i].browseURL + '">' +
                          '</div>' +
                          '<div class="block-info">' +
                              '<span class="scene-info">' + results[i].sceneID + '</span>' +
                              '<span class="scene-info"><svg class="icon inline-block"><use xlink:href="#icon-clock"/></svg> ' + results[i].date + '</span>' +
                          '</div>' +
                      '</div>'
                );
            }

        } else {
            $('.errorMessage').removeClass('none');
        }
    })
    .always(function () {
        $('.spin').addClass('none');
    })
    .fail(function () {
        $('.errorMessage').removeClass('none');
    });
};


const initScene = (sceneID, sceneDate) => {
    $(".metaloader").removeClass('none');
    $('.errorMessage').addClass('none');

    let min = $("#minCount").val();
    let max = $("#maxCount").val();
    const query = `${sentinel_tiler_url}/sentinel/metadata/${sceneID}?'pmim=${min}&pmax=${max}`;

    $.getJSON(query, function (data) {
        scope.imgMetadata = data;
        updateRasterTile();
        $(".sentinel-info").removeClass('none');
        $(".sentinel-info .s2id").text(sceneID);
        $(".sentinel-info .s2date").text(sceneDate);
    })
        .fail(function () {
            if (map.getSource('sentinel-tiles')) map.removeSource('sentinel-tiles');
            if (map.getLayer('sentinel-tiles')) map.removeLayer('sentinel-tiles');
            $(".sentinel-info span").text('');
            $(".sentinel-info").addClass('none');
            $('.errorMessage').removeClass('none');
        })
        .always(function () {
            $('.metaloader').addClass('none');
        });
};


const updateRasterTile = () => {
    if (map.getSource('sentinel-tiles')) map.removeSource('sentinel-tiles');
    if (map.getLayer('sentinel-tiles')) map.removeLayer('sentinel-tiles');

    let meta = scope.imgMetadata;

    let rgb = $(".img-display-options .toggle-group input:checked").attr("data");
    const bands = rgb.split(',');

    // NOTE: Calling 512x512px tiles is a bit longer but gives a
    // better quality image and reduce the number of tiles requested

    // HACK: Trade-off between quality and speed. Setting source.tileSize to 512 and telling landsat-tiler
    // to get 256x256px reduces the number of lambda calls (but they are faster)
    // and reduce the quality because MapboxGl will oversample the tile.

    const tileURL = `${sentinel_tiler_url}/sentinel/tiles/${meta.sceneid}/{z}/{x}/{y}.png?` +
        `rgb=${rgb}&tile=256` +
        `&histo=${meta.rgbMinMax[bands[0]]}-${meta.rgbMinMax[bands[1]]}-${meta.rgbMinMax[bands[2]]}`;

    const attrib = '<span> &copy; Copernicus / ESA 2017 | </span>';

    $(".sentinel-info .s2rgb").text(rgb.toString());

    map.addSource('sentinel-tiles', {
        type: "raster",
        tiles: [tileURL],
        attribution : attrib,
        bounds: scope.imgMetadata.bounds,
        minzoom: 7,
        maxzoom: 15,
        tileSize: 256
    });

    map.addLayer({
        'id': 'sentinel-tiles',
        'type': 'raster',
        'source': 'sentinel-tiles'
    });
};


const updateMetadata = () => {
    if (!map.getSource('sentinel-tiles')) return;
    initScene(scope.imgMetadata.sceneid, scope.imgMetadata.date);
};


$(".img-display-options .toggle-group").change(function () {
    if (map.getSource('sentinel-tiles')) updateRasterTile();
});


document.getElementById("btn-clear").onclick = () => {
  if (map.getLayer('sentinel-tiles')) map.removeLayer('sentinel-tiles');
  if (map.getSource('sentinel-tiles')) map.removeSource('sentinel-tiles');
  map.setFilter("S2_Highlighted", ["in", "Name", ""]);
  map.setFilter("S2_Selected", ["in", "Name", ""]);

  $('.list-img').scrollLeft(0);
  $('.list-img').empty();

  $(".metaloader").addClass('off');
  $('.errorMessage').addClass('none');
  $(".sentinel-info span").text('');
  $(".sentinel-info").addClass('none');

  scope = {};

  $("#minCount").val(5);
  $("#maxCount").val(95);

  $(".img-display-options .toggle-group input").prop('checked', false);
  $(".img-display-options .toggle-group input[data='04,03,02']").prop('checked', true);

  $('.map').removeClass('in');
  $('.right-panel').removeClass('in');
  map.resize();

};

////////////////////////////////////////////////////////////////////////////////

var map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/vincentsarago/ciynpp13900842rqqtfbzll8x',
    center: [-70.50, 40],
    zoom: 3,
    attributionControl: true,
    minZoom: 3,
    maxZoom: 15
});

map.addControl(new mapboxgl.NavigationControl(), 'top-right');

map.on('mousemove', function (e) {
    const features = map.queryRenderedFeatures(e.point, {layers: ['sentinel-grid']});

    if (features.length !== 0) {
        const pr = ['any'];
        features.forEach(function (e) {
            pr.push(["==", "Name", e.properties.Name]);
        });
        map.setFilter("S2_Highlighted", pr);
    } else {
        map.setFilter("S2_Highlighted", ["in", "Name", ""]);
    }
});

map.on('click', function (e) {
  $(".right-panel").addClass('in');
  $('.spin').removeClass('none');
  const features = map.queryRenderedFeatures(e.point, {layers: ['sentinel-grid']});

  if (features.length !== 0) {
      $('.map').addClass('in');
      $('.list-img').removeClass('none');
      map.resize();

      const pr = ['any'];
      features.forEach(function (e) {
          pr.push(["==", "Name", e.properties.Name]);
      });
      map.setFilter("S2_Selected", pr);

      buildQueryAndRequestS2(features);

      const geojson = {
        'type': 'FeatureCollection',
        'features': features
      };

      const extent = turf.bbox(geojson);
      const llb = mapboxgl.LngLatBounds.convert([[extent[0], extent[1]], [extent[2], extent[3]]]);
      map.fitBounds(llb, {padding: 50});

  } else {
      $('.spin').addClass('none');
      map.setFilter("S2_Selected", ["in", "PATH", ""]);
  }
});

map.on('load', function () {
    map.addSource('sentinel', {
        "type": "vector",
        "url": "mapbox://vincentsarago.0qowxm38"
    });

    map.addLayer({
        "id": "S2_Highlighted",
        "type": "fill",
        "source": "sentinel",
        "source-layer": "Sentinel2_Grid",
        "paint": {
            "fill-outline-color": "#1386af",
            "fill-color": "#0f6d8e",
            "fill-opacity": 0.3
        },
        "filter": ["in", "Name", ""]
    });

    map.addLayer({
        "id": "S2_Selected",
        "type": "fill",
        "source": "sentinel",
        "source-layer": "Sentinel2_Grid",
        "paint": {
            "fill-outline-color": "#FFF",
            "fill-color": "#FFF",
            "fill-opacity": 0.2
        },
        "filter": ["in", "Name", ""]
    });

    $(".loading-map").addClass('off');
});
