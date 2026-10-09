"""Network analysis: aksesibilitas kebun ke pengepul + lokasi pengepul baru.
Jalankan: python network.py <folder_WEBGIS> <folder_data>
Butuh: numpy, scipy, networkx, pillow, tifffile. Input: jalan.json, kebun.json, Pengepul.json (Esri JSON, UTM 48S)
              + TIFF kesesuaian & tutupan lahan."""
import sys, json, math, numpy as np, networkx as nx, tifffile
from PIL import Image
from scipy.spatial import cKDTree
from itertools import combinations
sys.path.insert(0, __file__.rsplit('/',1)[0] if '/' in __file__ else '.')
from convert_utils import utm_ll
Image.MAX_IMAGE_PIXELS = None
SRC, OUT = sys.argv[1], sys.argv[2]

# ---------- PARAMETER (ubah di sini) ----------
SPASI     = 10      # m, jarak titik hasil densifikasi jalan
SAMBUNG   = 12      # m, titik dari jalan berbeda yang lebih dekat dari ini dianggap tersambung
N_BARU    = 2       # jumlah pengepul baru
MIN_JARAK = 500     # m, pengepul baru minimal sekian meter dari pengepul eksisting (jalur jaringan)
KELAS_TINGGI, KELAS_SEDANG = 500, 1500   # m, batas kelas aksesibilitas
KES_BOLEH = {1, 2}  # nilai raster kesesuaian yang boleh dipakai: 1 = S1, 2 = S2 (3 = N, tidak sesuai)
TUTUP_DILARANG = {1, 2, 7, 8}  # mangrove, hutan, perairan, tambak
# ----------------------------------------------

def load(fn): return json.load(open(f"{SRC}/{fn}.json"))
roads = [np.array(p) for f in load("jalan")["features"] for p in f["geometry"]["paths"]]
kebun = load("kebun")["features"]; peng = load("Pengepul")["features"]

# 1. graf: densifikasi, sambung titik dari jalan berbeda yang berdekatan
G = nx.Graph(); pts = []; lid = []
for li, r in enumerate(roads):
    prev = None
    for a, b in zip(r[:-1], r[1:]):
        L = np.hypot(*(b-a)); n = max(1, int(round(L/SPASI)))
        for k in range(n+1):
            if k == 0 and prev is not None: continue
            p = a + (b-a)*k/n; pts.append(p); lid.append(li); i = len(pts)-1
            if prev is not None: G.add_edge(prev, i, weight=float(np.hypot(*(p-pts[prev]))))
            prev = i
pts = np.array(pts); lid = np.array(lid)
for i, j in cKDTree(pts).query_pairs(SAMBUNG):
    if lid[i] != lid[j] and not G.has_edge(i, j): G.add_edge(i, j, weight=float(np.hypot(*(pts[i]-pts[j]))))
comps = sorted(nx.connected_components(G), key=len, reverse=True)
print(f"jalan: {len(roads)} garis, {len(pts)} titik, {len(comps)} komponen terhubung (terbesar {len(comps[0])} titik)")
tree = cKDTree(pts)
def snap(feat):
    d, i = tree.query([feat["geometry"]["x"], feat["geometry"]["y"]]); return int(i), float(d)

# 2. aksesibilitas eksisting
ps = [snap(f) for f in peng]; ks = [snap(f) for f in kebun]
dist_e = nx.multi_source_dijkstra_path_length(G, [p[0] for p in ps], weight="weight")
jarak_e = np.array([dist_e.get(k[0], np.inf) + k[1] + min(p[1] for p in ps) for k in ks])

# 3. kandidat: titik jalan dgn kesesuaian & tutupan layak
def raster(name):
    with tifffile.TiffFile(f"{SRC}/{name}.tif") as t:
        pg = t.pages[0]; tie = pg.tags[33922].value
        a = (np.array(Image.open(f"{SRC}/{name}.tif"))//17) if pg.bitspersample == 4 else pg.asarray()
    return a, tie[3], tie[4]
kes, kx, ky = raster("KESESUAIAN LAHAN PERTANIAN2")
# kode raster baru: 5=S1, 4=S2, 3=N, 127=nodata -> dipetakan ke 1=S1, 2=S2, 3=N (0=nodata)
_k = np.zeros(kes.shape, np.uint8)
for _s, _d in ((5, 1), (4, 2), (3, 3)): _k[kes == _s] = _d
kes = _k; tut, tx, ty = raster("TUTUPAN LAHAN")
def sample(a, x0, y0, x, y, w=25):
    c, r = int(x-x0), int(y0-y); win = a[max(r-w,0):r+w+1, max(c-w,0):c+w+1]
    return win
def status(i):
    p = pts[i]; ks_ = sample(kes, kx, ky, *p); ks_ = ks_[(ks_ > 0) & (ks_ < 100)]
    tt = sample(tut, tx, ty, *p); tt = tt[tt > 0]
    if ks_.size == 0 or tt.size == 0 or np.bincount(ks_).argmax() not in KES_BOLEH: return "kes"
    if np.bincount(tt).argmax() in TUTUP_DILARANG: return "tutupan"
    if dist_e.get(i, 0) < MIN_JARAK: return "dekat"
    return "layak"
utama = comps[0]
sampel = [i for i in utama if i % 5 == 0]
st = {i: status(i) for i in sampel}
cand = [i for i in sampel if st[i] == "layak"]
print(f"kandidat layak: {len(cand)}")

# 4. p-median: pilih N_BARU titik yang meminimalkan total jarak kebun ke pengepul terdekat
dk = [nx.single_source_dijkstra_path_length(G, k[0], weight="weight") for k in ks]
D = np.array([[dk[a].get(c, np.inf) + ks[a][1] for c in cand] for a in range(len(ks))])
best = jarak_e.copy(); pilih = []
for _ in range(N_BARU):
    tot = [np.minimum(best, D[:, j]).sum() if j not in pilih else np.inf for j in range(len(cand))]
    j = int(np.argmin(tot)); pilih.append(j); best = np.minimum(best, D[:, j])
jarak_b = best
print(f"rata-rata jarak kebun ke pengepul: {jarak_e.mean():.0f} m -> {jarak_b.mean():.0f} m")
kel = lambda d: "Tinggi" if d <= KELAS_TINGGI else "Sedang" if d <= KELAS_SEDANG else "Rendah"
for nm, J in (("sekarang", jarak_e), ("setelah usulan", jarak_b)):
    print(nm, {k: sum(kel(d) == k for d in J) for k in ("Tinggi", "Sedang", "Rendah")})

# 5. ekspor GeoJSON WGS84
def pt(x, y, props):
    la, lo = utm_ll(x, y); return {"type":"Feature","properties":props,"geometry":{"type":"Point","coordinates":[round(lo,6),round(la,6)]}}
fc = lambda f: {"type":"FeatureCollection","features":f}
feats = [pt(f["geometry"]["x"], f["geometry"]["y"], {"No": f["attributes"]["No"], "Nama": f["attributes"]["Jenis Kebun"].strip(), "Komoditas": ", ".join(s.strip() for s in f["attributes"]["Komoditas"].split(",")),
         "Foto": f'data/foto/kebun-{f["attributes"]["No"]:02d}.jpg', "jarak_m": int(round(jarak_e[i])), "kelas": kel(jarak_e[i]),
         "jarak_baru_m": int(round(jarak_b[i])), "kelas_baru": kel(jarak_b[i])}) for i, f in enumerate(kebun)]
json.dump(fc(feats), open(f"{OUT}/pengepul/kebun.geojson", "w"), ensure_ascii=False)
us = []
for n, j in enumerate(pilih, 1):
    x, y = pts[cand[j]]; melayani = int(sum(D[a, j] <= jarak_e[a] for a in range(len(ks))))
    us.append(pt(x, y, {"prioritas": n, "kebun_terlayani": melayani, "jarak_ke_eksisting_m": int(dist_e.get(cand[j], 0))}))
json.dump(fc(us), open(f"{OUT}/pengepul/pengepul_usulan.geojson", "w"))
jl = []
for r in roads:
    ll = [utm_ll(x, y) for x, y in r]; jl.append({"type":"Feature","properties":{},"geometry":{"type":"LineString","coordinates":[[round(lo,6),round(la,6)] for la, lo in ll]}})
json.dump(fc(jl), open(f"{OUT}/pengepul/jalan.geojson", "w"))

# 6. data untuk visualisasi proses di web
from collections import Counter
ll = lambda x, y: [round(utm_ll(x, y)[1], 6), round(utm_ll(x, y)[0], 6)]
best1 = np.minimum(jarak_e, D[:, pilih[0]])
kf = []
for i in sampel:
    pr = {"s": st[i]}
    if st[i] == "layak":
        j = cand.index(i); pr["t1"] = int(round(np.minimum(jarak_e, D[:, j]).sum())); pr["t2"] = int(round(np.minimum(best1, D[:, j]).sum()))
    kf.append({"type":"Feature","properties":pr,"geometry":{"type":"Point","coordinates":ll(*pts[i])}})
json.dump(fc(kf), open(f"{OUT}/pengepul/kandidat.geojson", "w"))
def jalur(sumber, jarak, fn):
    paths = nx.multi_source_dijkstra_path(G, sumber, weight="weight"); out = []
    for a, f in enumerate(kebun):
        if ks[a][0] not in paths: continue
        co = [ll(f["geometry"]["x"], f["geometry"]["y"])] + [ll(*pts[k]) for k in paths[ks[a][0]]]
        out.append({"type":"Feature","properties":{"No":f["attributes"]["No"],"Nama":f["attributes"]["Jenis Kebun"].strip(),"jarak_m":int(round(jarak[a])),"kelas":kel(jarak[a])},"geometry":{"type":"LineString","coordinates":co}})
    json.dump(fc(out), open(f"{OUT}/pengepul/{fn}.geojson", "w"))
jalur([p[0] for p in ps], jarak_e, "jalur_eksisting")
jalur([p[0] for p in ps] + [cand[j] for j in pilih], jarak_b, "jalur_baru")
it = []; b = jarak_e.copy()
for k, j in enumerate(pilih, 1):
    sb = b.sum(); b = np.minimum(b, D[:, j])
    it.append({"ke": k, "total_sebelum": int(sb), "total_sesudah": int(b.sum()), "lokasi": ll(*pts[cand[j]])})
json.dump({"n_garis": len(roads), "n_titik": len(pts), "n_komponen": len(comps), "n_kebun": len(ks), "n_eks": len(ps), "spasi": SPASI,
  "sambung": SAMBUNG, "min_jarak": MIN_JARAK, "counts": dict(Counter(st.values())), "total_awal": int(jarak_e.sum()),
  "rata_awal": float(jarak_e.mean()), "rata_akhir": float(jarak_b.mean()), "iter": it}, open(f"{OUT}/proses.json", "w"))
print("selesai")
