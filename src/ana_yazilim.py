import sys
import random
import csv
import time
import os
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QGridLayout, QLabel, QVBoxLayout, QHBoxLayout,
                             QPlainTextEdit, QPushButton, QMessageBox)
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
import pyqtgraph as pg

try:
    import serial
except ImportError:
    serial = None

SIMULASYON_MODU       = True
SERI_PORT             = 'COM3'
BAUD_RATE             = 115200
KRITIK_VOLTAJ         = 6.6

RAMPA_BEKLEME_SN      = 5
VERI_FREKANSI_SN      = 0.2

HABERLESME_TIMEOUT_SN = 120     
BAGLANTI_TIMEOUT      = 3.0

LOG_DIZINI = "telemetri_kayitlari"
os.makedirs(LOG_DIZINI, exist_ok=True)


class VeriIsleyici(QThread):
    sinyal           = pyqtSignal(dict)
    firlatma_engeli  = pyqtSignal()      

    def __init__(self):
        super().__init__()
        self._haberlesme_onay = False    

    def haberlesme_onayla(self):
        """Ana pencere haberleşme kurulunca bu metodu çağırır."""
        self._haberlesme_onay = True

    def run(self):
        if SIMULASYON_MODU:
            self.simulasyon_baslat()
        else:
            self.gercek_port_baslat()

    def simulasyon_baslat(self):
        
        bekleme_log = True
        while not self._haberlesme_onay:
            if bekleme_log:
                self.firlatma_engeli.emit()   
                bekleme_log = False
            time.sleep(0.2)

        irtifa           = 0
        yukseliyor       = True
        ucusun_sonu      = False
        baslangic_enlem  = 38.358420
        baslangic_boylam = 33.682111
        enlem  = baslangic_enlem
        boylam = baslangic_boylam

        adim_sayisi = int(RAMPA_BEKLEME_SN / VERI_FREKANSI_SN)
        for _ in range(adim_sayisi):
            self.sinyal.emit({
                "irtifa": 0, "ivme": 0.0, "hiz": 0.0, "sicaklik": 25.0,
                "nem": 44.0, "basinc": 1013.25, "pm25": 40.0, "pm10": 52.0,
                "enlem": enlem, "boylam": boylam,
                "batarya": 7.4, "yukseliyor": True
            })
            time.sleep(VERI_FREKANSI_SN)

        hedef_enlem  = baslangic_enlem
        hedef_boylam = baslangic_boylam
        while not ucusun_sonu:
            if yukseliyor:
                irtifa += random.randint(30, 60)
                ivme = random.uniform(6.5, 9.5) if irtifa < 800 else random.uniform(-1.5, -0.5)
                hiz  = random.uniform(100, 150) if irtifa < 800 else random.uniform(20, 60)
                if irtifa >= 3000:
                    yukseliyor   = False
                    hedef_enlem  = baslangic_enlem  + random.uniform(-0.03, 0.03)
                    hedef_boylam = baslangic_boylam + random.uniform(-0.03, 0.03)
            else:
                hiz    = random.uniform(9, 20)
                irtifa -= int(hiz / 5)
                ivme   = random.uniform(-0.1, 0.2)
                enlem  += (hedef_enlem  - enlem)  * 0.05
                boylam += (hedef_boylam - boylam) * 0.05
                if irtifa <= 0:
                    irtifa     = 0
                    enlem      = hedef_enlem
                    boylam     = hedef_boylam
                    ucusun_sonu = True

            if yukseliyor:
                enlem  += random.uniform(-0.00005, 0.00005)
                boylam += random.uniform(-0.00005, 0.00005)

            pm25     = (40 - (irtifa / 100)) + (15 if 1400 < irtifa < 1600 else 0) + random.uniform(-1, 1)
            pm10     = pm25 * random.uniform(1.2, 1.4)
            sicaklik = 25 - (irtifa / 200) + random.uniform(-0.2, 0.2)
            nem      = 44 + (irtifa / 180) + random.uniform(-1, 1)
            basinc   = 1013.25 - (irtifa / 8.5)
            batarya  = 7.4 - (irtifa / 10000)

            self.sinyal.emit({
                "irtifa": irtifa, "ivme": ivme, "hiz": hiz,
                "sicaklik": sicaklik, "nem": nem, "basinc": basinc,
                "pm25": max(0, pm25), "pm10": max(0, pm10),
                "enlem": enlem, "boylam": boylam,
                "batarya": batarya, "yukseliyor": yukseliyor
            })
            time.sleep(VERI_FREKANSI_SN)

    def gercek_port_baslat(self):
        if not serial:
            return
        
        while not self._haberlesme_onay:
            time.sleep(0.2)
        try:
            ser = serial.Serial(SERI_PORT, BAUD_RATE, timeout=1)
            while True:
                if ser.in_waiting > 0:
                    line   = ser.readline().decode('utf-8').strip()
                    parts  = line.split(',')
                    if len(parts) >= 11:
                        self.sinyal.emit({
                            "irtifa":     float(parts[0]),
                            "ivme":       float(parts[1]),
                            "hiz":        float(parts[2]),
                            "sicaklik":   float(parts[3]),
                            "nem":        float(parts[4]),
                            "basinc":     float(parts[5]),
                            "pm25":       float(parts[6]),
                            "pm10":       float(parts[7]),
                            "enlem":      float(parts[8]),
                            "boylam":     float(parts[9]),
                            "batarya":    float(parts[10]),
                            "yukseliyor": True
                        })
        except Exception:
            pass

# HAKEM PENCERESİ
class HakemPenceresi(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HAKEM EKRANI - SUPERNOVA")
        self.setGeometry(700, 50, 680, 480)
        self.setStyleSheet("background-color:#1a1a2e; color:white;")

        merkez = QWidget()
        self.setCentralWidget(merkez)
        ana = QVBoxLayout(merkez)

        baslik = QLabel("SUPERNOVA - HAKEM TAKİP EKRANI")
        baslik.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        baslik.setStyleSheet("color:#e2b96f; padding:8px;")
        ana.addWidget(baslik)

        self.durum_lab = QLabel("DURUM: BEKLENİYOR")
        self.durum_lab.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.durum_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ana.addWidget(self.durum_lab)

        izgara = QGridLayout()
        ana.addLayout(izgara)
        alanlar = [
            ("İrtifa (m)", 0,0), ("Dikey Hız (m/s)", 0,1), ("İvme (g)",     0,2),
            ("Sıcaklık",   1,0), ("Nem (%)",          1,1), ("Basınç (hPa)", 1,2),
            ("PM 2.5",     2,0), ("PM 10",            2,1), ("Batarya (V)",  2,2),
            ("Enlem",      3,0), ("Boylam",           3,1),
        ]
        self.kutular = {}
        for isim, r, c in alanlar:
            v = QVBoxLayout()
            v.addWidget(QLabel(isim))
            lbl = QLabel("-")
            lbl.setStyleSheet(
                "background:#0f3460; border:2px solid #e2b96f;"
                "padding:10px; font-size:20px; font-weight:bold; color:white;"
            )
            v.addWidget(lbl)
            izgara.addLayout(v, r, c)
            self.kutular[isim] = lbl

        self.baglanti_lab = QLabel("● BAĞLANTI: AKTİF")
        self.baglanti_lab.setStyleSheet("color:#2ecc71; font-size:14px; font-weight:bold;")
        self.baglanti_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ana.addWidget(self.baglanti_lab)

    def guncelle(self, v, durum_str, durum_renk, baglanti_aktif, son_gps):
        self.durum_lab.setText(f"DURUM: {durum_str}")
        self.durum_lab.setStyleSheet(f"color:{durum_renk}; font-size:14px; font-weight:bold;")
        enlem  = v['enlem']  if baglanti_aktif else son_gps[0]
        boylam = v['boylam'] if baglanti_aktif else son_gps[1]

        self.kutular["İrtifa (m)"].setText(f"{v['irtifa']} m")
        self.kutular["Dikey Hız (m/s)"].setText(f"{v['hiz']:.1f}")
        self.kutular["İvme (g)"].setText(f"{v['ivme']:+.2f}")
        self.kutular["Sıcaklık"].setText(f"{v['sicaklik']:.2f} °C")
        self.kutular["Nem (%)"].setText(f"{v['nem']:.2f}")
        self.kutular["Basınç (hPa)"].setText(f"{v['basinc']:.1f}")
        self.kutular["PM 2.5"].setText(f"{v['pm25']:.2f}")
        self.kutular["PM 10"].setText(f"{v['pm10']:.2f}")
        self.kutular["Batarya (V)"].setText(f"{v['batarya']:.2f}")
        self.kutular["Enlem"].setText(f"{enlem:.6f}")
        self.kutular["Boylam"].setText(f"{boylam:.6f}")

        if baglanti_aktif:
            self.baglanti_lab.setText("● BAĞLANTI: AKTİF")
            self.baglanti_lab.setStyleSheet("color:#2ecc71; font-size:14px; font-weight:bold;")
        else:
            self.baglanti_lab.setText("!! BAĞLANTI KESİLDİ - Son GPS donduruldu")
            self.baglanti_lab.setStyleSheet("color:#e74c3c; font-size:14px; font-weight:bold;")


class ProfesyonelYKI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TEKNOFEST YKI - SUPERNOVA")
        self.setGeometry(50, 50, 1400, 950)

        self.son_veri_zamani      = time.time()
        self.baglanti_aktif       = True
        self.son_gps              = (38.358420, 33.682111)

        
        self.hab_sayac_calisiyor  = False
        self.hab_kalan_sure       = HABERLESME_TIMEOUT_SN
        self.haberlesme_saglandi  = False

        # CSV
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_dosya = open(
            os.path.join(LOG_DIZINI, f"ucus_{ts}.csv"), "w", newline="", encoding="utf-8"
        )
        self.csv_yazar = csv.writer(self.csv_dosya)
        self.csv_yazar.writerow([
            "zaman","irtifa","hiz","ivme","sicaklik","nem",
            "basinc","pm25","pm10","enlem","boylam","batarya"
        ])

        # Hakem penceresi
        self.hakem = HakemPenceresi()
        self.hakem.show()

       
        ana_w = QWidget()
        self.setCentralWidget(ana_w)
        ana = QVBoxLayout(ana_w)

       
        ust = QHBoxLayout()
        self.logo = QLabel()
        pix = QPixmap("supernova_logo.jpeg")
        if not pix.isNull():
            self.logo.setPixmap(pix.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio))
        ust.addWidget(self.logo)

        bv = QVBoxLayout()
        lbl_takim = QLabel("SUPERNOVA ROKET TAKIMI")
        lbl_takim.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        self.ucus_durumu = QLabel("DURUM: BEKLENIYOR")
        self.ucus_durumu.setStyleSheet("color:gray; font-size:22px; font-weight:bold;")
        bv.addWidget(lbl_takim, alignment=Qt.AlignmentFlag.AlignCenter)
        bv.addWidget(self.ucus_durumu, alignment=Qt.AlignmentFlag.AlignCenter)
        ust.addLayout(bv)

        sag = QVBoxLayout()
        self.batarya_lab  = QLabel("BATARYA: 0.00 V")
        self.batarya_lab.setStyleSheet("font-size:18px; font-weight:bold;")
        self.kamera_lab   = QLabel("KAMERA: KAYITTA")
        self.kamera_lab.setStyleSheet("color:#e67e22; font-size:16px; font-weight:bold;")
        self.baglanti_lab = QLabel("● BAĞLANTI: AKTİF")
        self.baglanti_lab.setStyleSheet("color:#27ae60; font-size:15px; font-weight:bold;")
        for w in (self.batarya_lab, self.kamera_lab, self.baglanti_lab):
            sag.addWidget(w)
        ust.addLayout(sag)
        ana.addLayout(ust)

        
        hab_satir = QHBoxLayout()

        hab_etiket = QLabel("UKB AKTİF → HABERLEŞMEYE KALAN:")
        hab_etiket.setStyleSheet("font-size:13px; font-weight:bold;")
        hab_satir.addWidget(hab_etiket)

        self.hab_sayac_lab = QLabel("02:00")
        self.hab_sayac_lab.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        self.hab_sayac_lab.setStyleSheet(
            "background:#222; color:#aaaaaa; padding:5px 16px; border-radius:5px;"
        )
        hab_satir.addWidget(self.hab_sayac_lab)

        self.btn_ukb = QPushButton("UKB Aktif Edildi")
        self.btn_ukb.setStyleSheet(
            "background:#2980b9; color:white; padding:5px 14px; "
            "border-radius:4px; font-weight:bold;"
        )
        self.btn_ukb.clicked.connect(self._ukb_aktif_edildi)
        hab_satir.addWidget(self.btn_ukb)

        self.btn_hab_sifirla = QPushButton("Sıfırla")
        self.btn_hab_sifirla.setStyleSheet(
            "background:#c0392b; color:white; padding:5px 12px; border-radius:4px;"
        )
        self.btn_hab_sifirla.clicked.connect(self._hab_sayac_sifirla)
        hab_satir.addWidget(self.btn_hab_sifirla)

        self.hab_durum_lab = QLabel("⚠ UKB aktif edilmeden fırlatma yapılamaz!")
        self.hab_durum_lab.setStyleSheet("color:#e67e22; font-size:13px; font-weight:bold;")
        hab_satir.addWidget(self.hab_durum_lab)

        hab_satir.addStretch()
        ana.addLayout(hab_satir)

        
        self.hab_timer = QTimer()
        self.hab_timer.setInterval(1000)
        self.hab_timer.timeout.connect(self._hab_sayac_guncelle)

        
        tabs = QTabWidget()
        ana.addWidget(tabs)

        dash = QWidget()
        tabs.addTab(dash, "Ana Aviyonik Sistem")
        self.grid = QGridLayout(dash)
        self.irtifa_v   = self._kutu("İrtifa (m):",      0,0)
        self.hiz_v      = self._kutu("Dikey Hız (m/s):", 0,1)
        self.ivme_v     = self._kutu("İvme X (g):",      0,2)
        self.sicaklik_v = self._kutu("Sıcaklık (C):",    1,0)
        self.nem_v      = self._kutu("Nem (%):",          1,1)
        self.basinc_v   = self._kutu("Basınç (hPa):",    1,2)
        self.pm25_v     = self._kutu("PM 2.5 (SPS30):",  2,0)
        self.pm10_v     = self._kutu("PM 10 (SPS30):",   2,1)
        self.enlem_v    = self._kutu("Enlem:",            3,0)
        self.boylam_v   = self._kutu("Boylam:",           3,1)

        analiz = QWidget()
        tabs.addTab(analiz, "Dikey Profil Analizi")
        gl = QVBoxLayout(analiz)
        self.pw = pg.PlotWidget(background='w', title="PM - İrtifa Profili")
        self.pw.addLegend()
        self.pw.setLabel('left',   'İrtifa', units='m')
        self.pw.setLabel('bottom', 'PM Konsantrasyonu')
        self.c25 = self.pw.plot([], [], pen=None, symbol='o',
                                symbolBrush='r', symbolSize=6, name="PM 2.5")
        self.c10 = self.pw.plot([], [], pen=None, symbol='t',
                                symbolBrush='b', symbolSize=6, name="PM 10")
        gl.addWidget(self.pw)

        self.x25, self.x10, self.yy = [], [], []

        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setMaximumBlockCount(500)
        self.terminal.setStyleSheet(
            "background:black; color:#00FF00; font-family:Consolas;"
        )
        ana.addWidget(QLabel("Ham Telemetri Akışı (RX):"))
        ana.addWidget(self.terminal)

        
        self.fs_timer = QTimer()
        self.fs_timer.setInterval(500)
        self.fs_timer.timeout.connect(self._baglanti_kontrol)
        self.fs_timer.start()

        
        self.thread = VeriIsleyici()
        self.thread.sinyal.connect(self.guncelle)
        self.thread.firlatma_engeli.connect(self._firlatma_engeli_goster)
        self.thread.start()

       
        self.hab_sayac_calisiyor = True
        self.hab_timer.start()
        self.hab_sayac_lab.setStyleSheet(
            "background:#222; color:#e67e22; padding:5px 16px; border-radius:5px;"
        )
        self.terminal.appendPlainText(
            ">> 2 dakika geri sayım basladi. Haberleşme sağlandığında 'UKB Aktif Edildi' butonuna basın."
        )

    
    def _kutu(self, isim, r, c):
        v = QVBoxLayout()
        v.addWidget(QLabel(isim))
        lbl = QLabel("0.00")
        lbl.setStyleSheet(
            "background:#fdfdfd; border:2px solid #333; "
            "padding:12px; font-size:22px; font-weight:bold;"
        )
        v.addWidget(lbl)
        self.grid.addLayout(v, r, c)
        return lbl

    def _firlatma_engeli_goster(self):
        self.terminal.appendPlainText(
            "!! UYARI: Haberleşme kurulmadan fırlatma yapılamaz! "
            "Lütfen önce 'UKB Aktif Edildi' butonuna basın."
        )

    
    def _ukb_aktif_edildi(self):
        if self.haberlesme_saglandi:
            return
        if not self.hab_sayac_calisiyor:
            return
        
        self.haberlesme_saglandi = True
        self.hab_timer.stop()
        self.btn_ukb.setEnabled(False)
        kalan = self.hab_kalan_sure
        dk, sn = divmod(kalan, 60)
        self.hab_sayac_lab.setStyleSheet(
            "background:#222; color:#2ecc71; padding:5px 16px; border-radius:5px;"
        )
        self.hab_durum_lab.setText(f"UKB AKTİF! Haberleşme kuruldu ({dk:02}:{sn:02} kaldı)")
        self.hab_durum_lab.setStyleSheet("color:#2ecc71; font-size:13px; font-weight:bold;")
        
        self.thread.haberlesme_onayla()
        self.terminal.appendPlainText(
            f">> UKB aktif edildi! Haberleşme kuruldu. Kalan süre: {dk:02}:{sn:02}. Fırlatma başlıyor..."
        )

    def _hab_sayac_sifirla(self):
        self.hab_timer.stop()
        self.hab_sayac_calisiyor = False
        self.haberlesme_saglandi = False
        self.hab_kalan_sure      = HABERLESME_TIMEOUT_SN
        self.hab_sayac_lab.setText("02:00")
        self.hab_sayac_lab.setStyleSheet(
            "background:#222; color:#e67e22; padding:5px 16px; border-radius:5px;"
        )
        self.hab_durum_lab.setText("Geri sayım sıfırlandı. Tekrar başlatılıyor...")
        self.hab_durum_lab.setStyleSheet("color:#e67e22; font-size:13px; font-weight:bold;")
        self.btn_ukb.setEnabled(True)
        
        self.thread._haberlesme_onay = False
        
        self.hab_sayac_calisiyor = True
        self.hab_timer.start()
        self.terminal.appendPlainText(">> Haberleşme sayacı sıfırlandı ve yeniden başlatıldı.")

    def _hab_sayac_guncelle(self):
        self.hab_kalan_sure -= 1
        dk, sn = divmod(self.hab_kalan_sure, 60)
        self.hab_sayac_lab.setText(f"{dk:02}:{sn:02}")

        if self.hab_kalan_sure <= 30:
            self.hab_sayac_lab.setStyleSheet(
                "background:#222; color:#e74c3c; padding:5px 16px; border-radius:5px;"
            )

        if self.hab_kalan_sure <= 0:
            self.hab_timer.stop()
            self.hab_sayac_lab.setStyleSheet(
                "background:#c0392b; color:white; padding:5px 16px; border-radius:5px;"
            )
            self.hab_durum_lab.setText("✖ SURE DOLDU - HABERLEŞME KURULAMADI!")
            self.hab_durum_lab.setStyleSheet("color:#e74c3c; font-size:13px; font-weight:bold;")
            self.terminal.appendPlainText(
                "!! 2 DAKİKA DOLDU - HABERLEŞME SAĞLANAMADI (Madde 4.8.25 - ELENME KRİTERİ)!"
            )
            QMessageBox.critical(
                self,
                "HABERLEŞME KURULAMADI!",
                "UKB aktifleşmesinden itibaren 2 dakika içinde\n"
                "Yer istasyonuyla HABERLEŞME SAĞLANAMADI!\n\n"
                "Şartname Madde 4.8.25 gereği takım elenebilir."
            )

    def _haberlesme_saglandi_isle(self):
        if self.hab_sayac_calisiyor and not self.haberlesme_saglandi:
            self.haberlesme_saglandi = True
            self.hab_timer.stop()
            
            self.thread.haberlesme_onayla()
            kalan = self.hab_kalan_sure
            dk, sn = divmod(kalan, 60)
            self.hab_sayac_lab.setStyleSheet(
                "background:#222; color:#2ecc71; padding:5px 16px; border-radius:5px;"
            )
            self.hab_durum_lab.setText(f"✔ UKB ile haberleşme kuruldu! ({dk:02}:{sn:02} kaldı)")
            self.hab_durum_lab.setStyleSheet("color:#2ecc71; font-size:13px; font-weight:bold;")
            self.terminal.appendPlainText(
                f">> UKB ile haberleşme kuruldu! Kalan süre: {dk:02}:{sn:02} (Madde 4.8.25 OK)."
            )


    def _baglanti_kontrol(self):
        aktif = (time.time() - self.son_veri_zamani) < BAGLANTI_TIMEOUT
        if aktif != self.baglanti_aktif:
            self.baglanti_aktif = aktif
            if aktif:
                self.baglanti_lab.setText("● BAĞLANTI: AKTİF")
                self.baglanti_lab.setStyleSheet(
                    "color:#27ae60; font-size:15px; font-weight:bold;"
                )
            else:
                gps = f"{self.son_gps[0]:.5f}, {self.son_gps[1]:.5f}"
                self.baglanti_lab.setText(f"!! BAĞLANTI KESİLDİ - Son GPS: {gps}")
                self.baglanti_lab.setStyleSheet(
                    "color:#e74c3c; font-size:15px; font-weight:bold;"
                )
                self.terminal.appendPlainText(
                    f"!! BAĞLANTI KOPTU - GPS donduruldu: {gps}"
                )

    def guncelle(self, v):
        self.son_veri_zamani = time.time()
        self.son_gps = (v['enlem'], v['boylam'])

        self._haberlesme_saglandi_isle()

        irtifa  = v['irtifa']
        ivme    = v['ivme']
        batarya = v['batarya']
        yuk     = v['yukseliyor']

        if irtifa < 10 and yuk:      d, r = "RAMPADA",              "blue"
        elif ivme > 5:               d, r = "MOTOR YANIYOR (BOOST)", "red"
        elif yuk:                    d, r = "SÜZÜLME (COAST)",        "orange"
        elif irtifa <= 0 and not yuk:d, r = "İNİŞ TAMAMLANDI",       "purple"
        else:                        d, r = "İNİŞE GEÇİLDİ (DESCENT)","green"

        self.ucus_durumu.setText(f"DURUM: {d}")
        self.ucus_durumu.setStyleSheet(f"color:{r}; font-size:22px; font-weight:bold;")

        krit = batarya <= KRITIK_VOLTAJ
        self.batarya_lab.setStyleSheet(
            f"font-size:18px; font-weight:bold; color:{'red' if krit else 'black'};"
        )
        self.batarya_lab.setText(
            f"BATARYA: {batarya:.2f} V{'  (KRITIK!)' if krit else ''}"
        )

        self.irtifa_v.setText(f"{irtifa} m")
        self.hiz_v.setText(f"{v['hiz']:.1f} m/s")
        self.ivme_v.setText(f"{v['ivme']:+.2f} g")
        self.sicaklik_v.setText(f"{v['sicaklik']:.2f} C")
        self.nem_v.setText(f"{v['nem']:.2f} %")
        self.basinc_v.setText(f"{v['basinc']:.1f} hPa")
        self.pm25_v.setText(f"{v['pm25']:.2f}")
        self.pm10_v.setText(f"{v['pm10']:.2f}")
        self.enlem_v.setText(f"{v['enlem']:.6f}")
        self.boylam_v.setText(f"{v['boylam']:.6f}")

        self.x25.append(v['pm25'])
        self.x10.append(v['pm10'])
        self.yy.append(irtifa)
        self.c25.setData(self.x25, self.yy)
        self.c10.setData(self.x10, self.yy)

        self.terminal.appendPlainText(
            f"RX >> IRT:{irtifa:04} | PM2.5:{v['pm25']:.1f} | "
            f"PM10:{v['pm10']:.1f} | BAT:{batarya:.2f} | "
            f"GPS:{v['enlem']:.5f},{v['boylam']:.5f}"
        )
        self.terminal.moveCursor(self.terminal.textCursor().MoveOperation.End)

        try:
            self.csv_yazar.writerow([
                datetime.now().strftime("%H:%M:%S.%f")[:-3],
                irtifa, f"{v['hiz']:.2f}", f"{ivme:.4f}",
                f"{v['sicaklik']:.2f}", f"{v['nem']:.2f}",
                f"{v['basinc']:.2f}", f"{v['pm25']:.2f}", f"{v['pm10']:.2f}",
                f"{v['enlem']:.7f}", f"{v['boylam']:.7f}", f"{batarya:.3f}"
            ])
            self.csv_dosya.flush()
        except Exception as e:
            self.terminal.appendPlainText(f"!! CSV HATASI: {e}")

        self.hakem.guncelle(v, d, r, self.baglanti_aktif, self.son_gps)

    def closeEvent(self, event):
        try:
            self.csv_dosya.close()
        except Exception:
            pass
        self.hakem.close()
        event.accept()


if __name__ == '__main__':
    app     = QApplication(sys.argv)
    pencere = ProfesyonelYKI()
    pencere.show()
    sys.exit(app.exec())