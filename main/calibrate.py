"""
Kalibrasyon ölçüm kaydedici.

Kullanım:
  python calibrate.py add "<etiket>" "<plan>" <sayac_watt> [saniye]
      AIDA64'ten <saniye> (varsayılan 30) boyunca 1 Hz örnek alır, ortalamasını
      akıllı sayaç değeriyle birlikte olcumler.jsonl dosyasına ekler.
  python calibrate.py list
      Kayıtlı ölçümleri tablo olarak gösterir.
  python calibrate.py fit [plan]
      Kayıtlardan Priz = taban + a*CPU + b*GPU regresyonu hesaplar.
      'disk' kelimesi geçen etiketler (HDD stresi) dışarıda bırakılır.
"""
import sys
import json
import time
import os
from live_tracker import AIDA64Reader

DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "olcumler.jsonl")
CPU_ID = "PCPUPKG"
GPU_ID = "PGPU1"


def sayi(v):
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def ekle(etiket, plan, sayac_w, saniye=30):
    reader = AIDA64Reader()
    toplam, adet = {}, {}
    cpu_ornek, gpu_ornek = [], []
    print(f"{saniye} sn ölçülüyor... (şimdi sayaçtaki W değerini sabit tut)")
    for _ in range(saniye):
        s = reader.read_sensors()
        if s:
            for k, v in s.items():
                f = sayi(v)
                if f is not None:
                    toplam[k] = toplam.get(k, 0.0) + f
                    adet[k] = adet.get(k, 0) + 1
            c, g = sayi(s.get(CPU_ID)), sayi(s.get(GPU_ID))
            if c is not None and g is not None:
                cpu_ornek.append(c)
                gpu_ornek.append(g)
        time.sleep(1)
    if not cpu_ornek:
        print("AIDA64 okunamadı, kayıt eklenmedi.")
        return
    ort = {k: toplam[k] / adet[k] for k in toplam}
    kayit = {
        "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
        "etiket": etiket,
        "plan": plan,
        "sayac_w": float(sayac_w),
        "cpu_w": sum(cpu_ornek) / len(cpu_ornek),
        "gpu_w": sum(gpu_ornek) / len(gpu_ornek),
        "cpu_min": min(cpu_ornek), "cpu_max": max(cpu_ornek),
        "gpu_min": min(gpu_ornek), "gpu_max": max(gpu_ornek),
        "sensorler": ort,
    }
    with open(DOSYA, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    print(f"KAYDEDİLDİ: {etiket} [{plan}] sayaç={sayac_w} W | "
          f"CPU ort {kayit['cpu_w']:.1f} ({kayit['cpu_min']:.0f}-{kayit['cpu_max']:.0f}) | "
          f"GPU ort {kayit['gpu_w']:.1f} ({kayit['gpu_min']:.0f}-{kayit['gpu_max']:.0f})")


def oku():
    if not os.path.exists(DOSYA):
        return []
    with open(DOSYA, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def listele():
    for k in oku():
        print(f"{k['zaman']} | {k['etiket']:<22} | {k['plan']:<10} | sayaç {k['sayac_w']:>5.0f} W | "
              f"CPU {k['cpu_w']:>6.1f} | GPU {k['gpu_w']:>6.1f}")


def coz(A, b):
    n = len(b)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for i in range(n):
        p = M[i][i]
        M[i] = [v / p for v in M[i]]
        for k in range(n):
            if k != i:
                f = M[k][i]
                M[k] = [a - f * c for a, c in zip(M[k], M[i])]
    return [M[i][n] for i in range(n)]


def fit(plan=None):
    veri = [k for k in oku() if "disk" not in k["etiket"].lower()
            and (plan is None or k["plan"] == plan)]
    if len(veri) < 4:
        print(f"En az 4 ölçüm gerekli (şu an {len(veri)}).")
        return
    satir = [[1.0, k["cpu_w"], k["gpu_w"]] for k in veri]
    y = [k["sayac_w"] for k in veri]
    AtA = [[sum(r[i] * r[j] for r in satir) for j in range(3)] for i in range(3)]
    Aty = [sum(r[i] * yy for r, yy in zip(satir, y)) for i in range(3)]
    t, a, b = coz(AtA, Aty)
    print(f"Priz = {t:.1f} + {a:.3f}*CPU + {b:.3f}*GPU   ({len(veri)} ölçüm, plan={plan or 'hepsi'})")
    en_buyuk = 0
    for k in veri:
        m = t + a * k["cpu_w"] + b * k["gpu_w"]
        fark = m - k["sayac_w"]
        en_buyuk = max(en_buyuk, abs(fark))
        print(f"  {k['etiket']:<22} [{k['plan']:<10}] sayaç {k['sayac_w']:>5.0f} | model {m:>6.1f} | fark {fark:+.1f}")
    print(f"En büyük sapma: {en_buyuk:.1f} W")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    kom = sys.argv[1] if len(sys.argv) > 1 else ""
    if kom == "add" and len(sys.argv) >= 5:
        ekle(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 30)
    elif kom == "list":
        listele()
    elif kom == "fit":
        fit(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print(__doc__)
