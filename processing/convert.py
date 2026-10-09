"""Ubah data WEBGIS (TIFF UTM 48S + JSON Esri) menjadi PNG + GeoJSON WGS84 untuk web.
Jalankan: python convert.py <folder_WEBGIS> <folder_output_data>
Butuh: numpy, pillow, tifffile"""
import sys, json, math, os
import numpy as np, tifffile
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
SRC, OUT = sys.argv[1], sys.argv[2]

from convert_utils import utm_ll

# Raster kesesuaian terbaru memakai kode 3=N, 4=S2, 5=S1 (127=nodata); dipetakan ke 1=S1, 2=S2, 3=N
REMAP = {"KESESUAIAN LAHAN PERTANIAN2": {5:1, 4:2, 3:3}}

def hexrgb(h): return [int(h[i:i+2],16) for i in (1,3,5)]
LAYERS = {  # file: (output, nodata, {nilai: (warna, label)})
 "CURAH HUJAN": ("curah_hujan", {1:("#c6dbef","2505 mm"),2:("#6baed6","2649 mm"),3:("#2171b5","2699 mm"),4:("#08306b","2819 mm")}),
 "ELEVASI": ("elevasi", {1:("#1a9850","0-50 m"),2:("#a6d96a","50-100 m"),3:("#fee08b","100-150 m"),4:("#fc8d59","150-200 m"),5:("#8c510a",">200 m")}),
 "KEMIRINGAN LERENG": ("lereng", {1:("#d73027",">30%"),2:("#fc8d59","15-30%"),3:("#fee08b","8-15%"),4:("#a6d96a","4-8%"),5:("#1a9850","0-4%")}),
 "KESESUAIAN LAHAN PERTANIAN2": ("kesesuaian_lahan", {1:("#1a9850","S1 (sangat sesuai)"),2:("#a6d96a","S2 (cukup sesuai)"),3:("#d73027","N (tidak sesuai)")}),
 "TUTUPAN LAHAN": ("tutupan_lahan", {1:("#2e8b57","Hutan mangrove"),2:("#1b5e20","Hutan"),3:("#616161","Jalan"),4:("#cddc39","Pertanian"),
   5:("#8bc34a","Perkebunan"),6:("#d7ccc8","Lahan terbuka"),7:("#2196f3","Perairan"),8:("#4dd0e1","Tambak"),9:("#9ccc65","Vegetasi"),10:("#e53935","Bangunan")}),
}
meta = {}
for name,(out,classes) in LAYERS.items():
    with tifffile.TiffFile(f"{SRC}/{name}.tif") as t:
        pg=t.pages[0]; tie=pg.tags[33922].value; h,w=pg.shape
        arr = np.array(Image.open(f"{SRC}/{name}.tif")) // 17 if pg.bitspersample==4 else pg.asarray()
    if name in REMAP:
        a2 = np.zeros(arr.shape, np.uint8)
        for src, dst in REMAP[name].items(): a2[arr==src] = dst
        arr = a2
    x0,y0=tie[3],tie[4]; x1,y1=x0+w,y0-h
    idx=np.zeros(arr.shape,np.uint8); pal=[0]*768
    for v,(col,_) in classes.items():
        idx[arr==v]=v; pal[v*3:v*3+3]=hexrgb(col)
    im=Image.fromarray(idx,"P"); im.putpalette(pal); im.save(f"{OUT}/kesesuaian/{out}.png",transparency=0,optimize=True)
    (la0,lo0),(la1,lo1)=utm_ll(x0,y1),utm_ll(x1,y0)   # (barat-daya),(timur-laut)
    meta[out]={"bounds":[[la0,lo0],[la1,lo1]],"classes":{str(v):{"warna":c,"label":l} for v,(c,l) in classes.items()}}
    print(out, f"{w}x{h}", meta[out]["bounds"])
json.dump(meta,open(f"{OUT}/kesesuaian/meta.json","w"),indent=1)

def esri_pts(fn, out, kolom):
    d=json.load(open(f"{SRC}/{fn}.json")); feats=[]
    for f in d["features"]:
        lat,lon=utm_ll(f["geometry"]["x"],f["geometry"]["y"])
        feats.append({"type":"Feature","properties":{k:f["attributes"].get(k) for k in kolom},"geometry":{"type":"Point","coordinates":[round(lon,6),round(lat,6)]}})
    json.dump({"type":"FeatureCollection","features":feats},open(f"{OUT}/pengepul/{out}.geojson","w"))
    print(out,len(feats))
esri_pts("Pengepul","pengepul_eksisting",["Nama"])
aoi=json.load(open(f"{SRC}/AOI.json"))
feats=[{"type":"Feature","properties":{"nama":aoi["features"][0]["attributes"].get("NAMOBJ")},"geometry":{"type":"Polygon","coordinates":[[[round(x,5),round(y,5)] for x,y in r] for r in aoi["features"][0]["geometry"]["rings"]]}}]
json.dump({"type":"FeatureCollection","features":feats},open(f"{OUT}/aoi.geojson","w")); print("aoi ok")
