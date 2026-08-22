from dataclasses import dataclass
import io
import json
import math
import os
import random
import struct
import sys
import wave

import pygame

# ============================================================
# ZALİM KRAL: TAHTIN GÖLGESİ — V18 (DİNAMİK ÖLÇEKLENDİRME & MOBİL UYUMLU)
# ============================================================

pygame.init()
pygame.mixer.init(frequency=22100, size=-16, channels=1)

# Sabit İç Çözünürlük (Tüm oyun tasarımı bu boyuta göre yapılmıştır)
INTERNAL_WIDTH = 1400
INTERNAL_HEIGHT = 850
FPS = 60

# Gerçek Pencere Ekranı (Yeniden boyutlandırılabilir)
SCREEN = pygame.display.set_mode(
    (INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.RESIZABLE
)
pygame.display.set_caption(
    "Zalim Kral — Tahtın Gölgesi (Dinamik Ölçeklendirmeli Sürüm)"
)

# Dahili Çizim Yüzeyi (Virtual Screen)
VIRTUAL_SCREEN = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))

CLOCK = pygame.time.Clock()

# ------------------------------------------------------------
# RENK PALETİ & ATMOSFER
# ------------------------------------------------------------
BG_STONE = (18, 16, 22)
STONE_BRICK = (28, 24, 34)
STONE_LINE = (12, 10, 15)
PANEL_SOLID = (24, 21, 30)
PANEL_2 = (35, 30, 42)
PANEL_HOVER = (52, 44, 60)

GOLD = (212, 175, 55)
GOLD_LIGHT = (240, 205, 100)
TEXT = (240, 230, 215)
TEXT_DIM = (150, 140, 130)

RED = (190, 45, 45)
RED_DARK = (90, 20, 20)
GREEN = (55, 170, 75)
BLUE = (65, 130, 190)
PURPLE = (140, 75, 185)
WHITE = (255, 255, 255)

# ------------------------------------------------------------
# FONTLAR
# ------------------------------------------------------------
FONT_TITLE = pygame.font.SysFont("Georgia", 28, bold=True)
FONT_BIG = pygame.font.SysFont("Georgia", 20, bold=True)
FONT = pygame.font.SysFont("Georgia", 15)
FONT_SMALL = pygame.font.SysFont("Georgia", 12)


# ============================================================
# 1. DİNAMİK MÜZİK VE SES MOTORU
# ============================================================
class MusicManager:

  def __init__(self):
    self.current_theme = None
    self.current_sound = None

  def play(self, theme):
    if self.current_theme != theme:
      self.current_theme = theme
      self.generate_and_play_dynamic_melody(theme)

  def generate_and_play_dynamic_melody(self, theme):
    try:
      if self.current_sound:
        self.current_sound.stop()
    except:
      pass

    scales = {
        "menu": [130.81, 164.81, 196.00, 246.94, 261.63],
        "play": [174.61, 220.00, 261.63, 329.63, 349.23],
        "intrigue": [185.00, 220.00, 233.08, 277.18, 329.63],
        "result": [261.63, 329.63, 392.00, 523.25],
        "gameover": [110.00, 98.00, 87.31, 77.78],
    }.get(theme, [220.00, 261.63, 329.63])

    sample_rate = 22100
    num_notes = 32
    buffer = io.BytesIO()

    with wave.open(buffer, "w") as wav_file:
      wav_file.setnchannels(1)
      wav_file.setsampwidth(2)
      wav_file.setframerate(sample_rate)
      frames = bytearray()
      rng = random.Random(random.randint(0, 999999))

      for _ in range(num_notes):
        freq = rng.choice(scales)
        duration = rng.choice([0.15, 0.2, 0.3, 0.35])
        samples_in_note = int(sample_rate * duration)

        for i in range(samples_in_note):
          t = i / sample_rate
          env = math.sin(math.pi * i / samples_in_note)
          val = (
              math.sin(2 * math.pi * freq * t) * 0.4
              + math.sin(2 * math.pi * (freq * 1.5) * t) * 0.2
              + (1.0 if math.sin(2 * math.pi * freq * 2 * t) > 0 else -1.0)
              * 0.05
          )
          sample = int(val * env * 6500)
          frames += struct.pack("<h", sample)

        rest_samples = int(sample_rate * 0.04)
        for _ in range(rest_samples):
          frames += struct.pack("<h", 0)

      wav_file.writeframes(frames)

    buffer.seek(0)
    try:
      self.current_sound = pygame.mixer.Sound(buffer)
      self.current_sound.set_volume(0.18)
      self.current_sound.play(-1)
    except:
      pass


music_mgr = MusicManager()


class SoundEffectManager:

  def __init__(self):
    self.ripples = []

  def create_beep(self, start_freq, end_freq, duration, volume=0.3):
    sample_rate = 22100
    num_samples = int(sample_rate * duration)
    buffer = io.BytesIO()
    with wave.open(buffer, "w") as wav_file:
      wav_file.setnchannels(1)
      wav_file.setsampwidth(2)
      wav_file.setframerate(sample_rate)
      frames = bytearray()
      for i in range(num_samples):
        t = i / sample_rate
        cfreq = start_freq + (end_freq - start_freq) * (i / num_samples)
        env = 1.0 - (i / num_samples)
        val = math.sin(2 * math.pi * cfreq * t)
        sample = int(val * env * 8000 * volume)
        frames += struct.pack("<h", sample)
      wav_file.writeframes(frames)
    buffer.seek(0)
    try:
      snd = pygame.mixer.Sound(buffer)
      snd.set_volume(volume)
      snd.play()
    except:
      pass

  def play_click(self):
    base = random.randint(600, 800)
    self.create_beep(base, base - 250, 0.07, 0.2)

  def play_win(self):
    self.create_beep(350, 700, 0.3, 0.3)

  def add_ripple(self, x, y):
    self.ripples.append({"x": x, "y": y, "radius": 5, "alpha": 200})
    self.play_click()

  def update_and_draw(self, surface):
    for r in self.ripples[:]:
      r["radius"] += 4
      r["alpha"] -= 12
      if r["alpha"] <= 0:
        self.ripples.remove(r)
        continue
      s = pygame.Surface((r["radius"] * 2, r["radius"] * 2), pygame.SRCALPHA)
      pygame.draw.circle(
          s,
          (212, 175, 55, max(0, r["alpha"])),
          (r["radius"], r["radius"]),
          r["radius"],
          2,
      )
      surface.blit(s, (r["x"] - r["radius"], r["y"] - r["radius"]))


click_fx = SoundEffectManager()


# ============================================================
# 2. GÖRSEL KALE MİMARİSİ & KARAKTER PORTRELERİ
# ============================================================
def draw_castle_walls(surface, tick_count):
  surface.fill(BG_STONE)

  brick_w, brick_h = 80, 40
  for y in range(0, INTERNAL_HEIGHT, brick_h):
    offset = (y // brick_h) % 2 * 40
    for x in range(-40, INTERNAL_WIDTH + 40, brick_w):
      bx = x + offset
      pygame.draw.rect(surface, STONE_BRICK, (bx, y, brick_w - 2, brick_h - 2))
      pygame.draw.rect(surface, STONE_LINE, (bx, y, brick_w - 2, brick_h - 2), 1)

  dais_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 320, 100, 640, 380)
  pygame.draw.rect(surface, (32, 27, 40), dais_rect, border_radius=16)
  pygame.draw.rect(surface, (60, 48, 35), dais_rect, 2, border_radius=16)

  win_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 130, 50, 260, 300)
  pygame.draw.ellipse(surface, (25, 40, 75), win_rect)
  pygame.draw.ellipse(surface, GOLD, win_rect, 3)
  pygame.draw.line(
      surface, GOLD, (INTERNAL_WIDTH // 2, 50), (INTERNAL_WIDTH // 2, 350), 2
  )
  pygame.draw.line(
      surface,
      GOLD,
      (INTERNAL_WIDTH // 2 - 120, 200),
      (INTERNAL_WIDTH // 2 + 120, 200),
      2,
  )

  throne_back = pygame.Rect(INTERNAL_WIDTH // 2 - 95, 130, 190, 310)
  pygame.draw.rect(surface, (45, 32, 22), throne_back, border_radius=16)
  pygame.draw.rect(surface, GOLD, throne_back, 3, border_radius=16)
  throne_seat = pygame.Rect(INTERNAL_WIDTH // 2 - 80, 330, 160, 55)
  pygame.draw.rect(surface, RED_DARK, throne_seat, border_radius=8)
  pygame.draw.rect(surface, GOLD, throne_seat, 2, border_radius=8)

  for x_pos in [60, INTERNAL_WIDTH - 160]:
    pygame.draw.rect(surface, (22, 19, 28), (x_pos, 0, 100, INTERNAL_HEIGHT))
    pygame.draw.rect(surface, (50, 42, 60), (x_pos, 0, 14, INTERNAL_HEIGHT))
    torch_y = 260
    flicker = math.sin(tick_count * 0.25 + x_pos) * 5
    pygame.draw.rect(
        surface, (80, 60, 35), (x_pos + 42, torch_y, 22, 45), border_radius=4
    )
    pygame.draw.circle(
        surface, (255, 150, 20), (x_pos + 53, torch_y - 12 + int(flicker)), 14
    )
    pygame.draw.circle(
        surface, (255, 230, 60), (x_pos + 53, torch_y - 10 + int(flicker)), 8
    )


def draw_character_card(surface, x, y, char):
  card_rect = pygame.Rect(x, y, 360, 140)
  pygame.draw.rect(surface, PANEL_2, card_rect, border_radius=12)
  pygame.draw.rect(surface, GOLD, card_rect, 2, border_radius=12)

  av_rect = pygame.Rect(x + 15, y + 15, 110, 110)
  col = (
      RED_DARK
      if "Kral" in char.title or "Prens" in char.title
      else (BLUE if "Komutan" in char.title or "Şövalye" in char.title else PURPLE)
  )
  pygame.draw.rect(surface, col, av_rect, border_radius=8)
  pygame.draw.rect(surface, GOLD, av_rect, 2, border_radius=8)
  pygame.draw.circle(surface, (210, 185, 160), (x + 70, y + 60), 32)

  draw_text(surface, char.name, FONT_BIG, GOLD, x + 135, y + 15)
  draw_text(surface, f"Unvan: {char.title}", FONT_SMALL, TEXT, x + 135, y + 45)
  draw_text(surface, f"Grup: {char.faction}", FONT_SMALL, TEXT_DIM, x + 135, y + 65)
  draw_text(
      surface,
      f"Sadakat: {char.loyalty} | Hırs: {char.ambition}",
      FONT_SMALL,
      TEXT,
      x + 135,
      y + 90,
  )


# ============================================================
# 3. VERİ YAPILARI
# ============================================================
@dataclass
class Character:
  id: int
  name: str
  title: str
  faction: str
  age: int
  ambition: int
  loyalty: int
  fear: int
  respect: int
  intelligence: int
  wealth: int
  alive: bool = True
  imprisoned: bool = False


@dataclass
class Faction:
  name: str
  power: int
  loyalty: int
  influence: int
  wealth: int


class Game:
  SAVE_FILE = "zalim_kral_v18_save.json"

  def __init__(self):
    self.state = "MENU"
    self.active_tab = "events"
    self.day = 1
    self.hour = 8
    self.max_days = 90
    self.rank = "Saray Uşağı"
    self.rank_level = 1

    self.gold = 35
    self.food = 40
    self.weapons = 25
    self.morale = 50
    self.stress = 10
    self.health = 100
    self.personal_influence = 5

    self.people = 50
    self.church = 50
    self.nobles = 40
    self.merchants = 45
    self.stability = 60
    self.intrigue = 30
    self.spy_network = 10

    self.characters = []
    self.factions = {}
    self.notifications = []
    self.current_event = None
    self.current_character = None
    self.current_result = ""
    self.enacted_edicts = []
    self.secrets = []  # Toplanan sırlar listesi

    self.event_history = []
    self.generate_world()

  def generate_world(self):
    self.characters.clear()
    self.factions.clear()

    factions_data = [
        ("Kraliyet Hanedanı", 80, 75, 85, 80),
        ("Kuzey Soyluları", 65, 50, 70, 60),
        ("Güney Tüccarları", 50, 60, 65, 95),
        ("Kilise & Rahipler", 55, 70, 80, 75),
        ("Ordu Komutanlığı", 75, 65, 60, 50),
        ("Saray Hizmetkarları", 40, 80, 40, 30),
    ]

    for data in factions_data:
      f = Faction(*data)
      self.factions[f.name] = f

    char_templates = [
        ("Kral V. Alistair", "Kral", "Kraliyet Hanedanı", 58, 40, 50, 60),
        ("Kraliçe Beatrix", "Kraliçe", "Kraliyet Hanedanı", 52, 70, 45, 70),
        ("Veliaht Prens Edward", "Veliaht", "Kraliyet Hanedanı", 26, 85, 40, 40),
        ("Başvezir Lord Sterling", "Başvezir", "Kuzey Soyluları", 61, 90, 35, 80),
        ("General Marcus", "Komutan", "Ordu Komutanlığı", 49, 65, 70, 75),
        ("Başpiskopos Ignatius", "Rahip", "Kilise & Rahipler", 64, 75, 60, 85),
        ("Hazine Müdürü Silas", "Tüccar", "Güney Tüccarları", 48, 60, 50, 70),
        ("Saray Aşçısı Ignis", "Hizmetkar", "Saray Hizmetkarları", 45, 30, 80, 50),
        ("Baş Başçavuş Boris", "Muhafız", "Ordu Komutanlığı", 42, 50, 65, 45),
        ("Baş Casus Vesper", "Casus", "Saray Hizmetkarları", 38, 80, 30, 95),
    ]

    for i, c_data in enumerate(char_templates):
      name, title, faction, age, amb, loy, intel = c_data
      char = Character(
          id=i,
          name=name,
          title=title,
          faction=faction,
          age=age,
          ambition=amb,
          loyalty=loy,
          fear=random.randint(20, 70),
          respect=random.randint(30, 85),
          intelligence=intel,
          wealth=random.randint(20, 80),
      )
      self.characters.append(char)

    self.generate_event()

  def get_character(self, char_id):
    for c in self.characters:
      if c.id == char_id:
        return c
    return None

  def alive_characters(self):
    return [c for c in self.characters if c.alive and not c.imprisoned]

  def update_rank_and_progression(self):
    if self.day >= 75 and self.personal_influence >= 70:
      self.rank = "Gölge İmparator"
      self.rank_level = 5
    elif self.day >= 50 and self.personal_influence >= 50:
      self.rank = "Başvezir"
      self.rank_level = 4
    elif self.day >= 30 and self.personal_influence >= 30:
      self.rank = "Kraliyet Danışmanı"
      self.rank_level = 3
    elif self.day >= 15 and self.personal_influence >= 15:
      self.rank = "Saray Muhafızı"
      self.rank_level = 2
    else:
      self.rank = "Saray Uşağı"
      self.rank_level = 1

  # ============================================================
  # 4. TÜM SENARYO VE OLAY FONKSİYONLARI
  # ============================================================
  def generate_event(self):
    living = self.alive_characters()
    if not living:
      return
    self.current_character = random.choice(living)

    if self.rank_level == 1:
      pool = [
          "SERVANT_GOSSIP",
          "KITCHEN_THEFT",
          "GUARD_BULLY",
          "NOBLE_ERRAND",
          "CLEANING_SECRET",
          "STABLE_RUMOR",
      ]
    elif self.rank_level == 2:
      pool = [
          "GUARD_BRIBE",
          "CORRIDOR_FIGHT",
          "SPY_WHISPER",
          "NOBLE_PLOT",
          "GATE_SMUGGLER",
          "WEAPON_SHORTAGE",
      ]
    elif self.rank_level == 3:
      pool = [
          "NOBLE_PLOT",
          "MILITARY_SUPPLY",
          "CHURCH_DECREE",
          "TAX_EVASION",
          "COURT_BRIEF",
          "DIPLOMAT_VISIT",
      ]
    else:
      pool = [
          "ASSASSINATION_ATTEMPT",
          "ESPIONAGE_REPORT",
          "COUP_WHISPER",
          "TREASURY_CRISIS",
          "REBELLION_SCARE",
          "CHURCH_SCHISM",
      ]

    filtered_pool = [e for e in pool if e not in self.event_history[-6:]]
    if not filtered_pool:
      filtered_pool = pool

    chosen_type = random.choice(filtered_pool)
    self.event_history.append(chosen_type)

    events_map = {
        "SERVANT_GOSSIP": self.ev_servant_gossip,
        "KITCHEN_THEFT": self.ev_kitchen_theft,
        "GUARD_BULLY": self.ev_guard_bully,
        "NOBLE_ERRAND": self.ev_noble_errand,
        "CLEANING_SECRET": self.ev_cleaning_secret,
        "STABLE_RUMOR": self.ev_stable_rumor,
        "GUARD_BRIBE": self.ev_guard_bribe,
        "CORRIDOR_FIGHT": self.ev_corridor_fight,
        "SPY_WHISPER": self.ev_spy_whisper,
        "NOBLE_PLOT": self.ev_noble_plot,
        "GATE_SMUGGLER": self.ev_gate_smuggler,
        "WEAPON_SHORTAGE": self.ev_weapon_shortage,
        "MILITARY_SUPPLY": self.ev_military_supply,
        "CHURCH_DECREE": self.ev_church_decree,
        "TAX_EVASION": self.ev_tax_evasion,
        "COURT_BRIEF": self.ev_court_brief,
        "DIPLOMAT_VISIT": self.ev_diplomat_visit,
        "ASSASSINATION_ATTEMPT": self.ev_assassination_attempt,
        "ESPIONAGE_REPORT": self.ev_espionage_report,
        "COUP_WHISPER": self.ev_coup_whisper,
        "TREASURY_CRISIS": self.ev_treasury_crisis,
        "REBELLION_SCARE": self.ev_rebellion_scare,
        "CHURCH_SCHISM": self.ev_church_schism,
    }
    self.current_event = events_map[chosen_type](self.current_character)

  def ev_servant_gossip(self, c):
    return {
        "title": f"Koridor Fısıltıları: {c.name}",
        "text": f"Hizmetkar {c.name}, soyluların arkamızdan iş çevirdiğini ve sarayda büyük bir kriz patlak vereceğini iddia ediyor.",
        "options": [
            {
                "text": "Bilgiyi dikkatle dinle ve hafızana kaz",
                "effects": {"intrigue": 6, "stress": 2, "personal_influence": 1},
                "add_secret": f"{c.name}'in Soylu Komplo İhbarı",
                "result": "Entrika bilgin ve sezgilerin keskinleşti.",
            },
            {
                "text": "Sırrı Baş Müfettişe rapor et",
                "effects": {"gold": 12, "stress": -2},
                "result": "Sadakatinden ötürü küçük bir bahşiş aldın.",
            },
            {
                "text": "Dedikoducuyu uyar ve uzaklaştır",
                "effects": {"stress": -4, "personal_influence": 2},
                "result": "Ortalık sakinleşti.",
            },
        ],
    }

  def ev_kitchen_theft(self, c):
    return {
        "title": "Kilerde Kayıp Erzak",
        "text": f"Aşçı {c.name}, kraliyet mutfağından değerli baharatların ve etlerin çalındığını söylüyor. Senden şüpheleniyorlar.",
        "options": [
            {
                "text": "Suçu başka bir hizmetkara at",
                "effects": {"intrigue": 5, "stress": 4, "personal_influence": 2},
                "result": "Şüpheden ustalıkla sıyrıldın.",
            },
            {
                "text": "Cezayı üstlen ve zararı öde",
                "effects": {"gold": -10, "food": -5, "stress": 6},
                "result": "Cebinden ödemek zorunda kaldın.",
            },
            {
                "text": "Aşçıya rüşvet verip kapat",
                "effects": {"gold": -8, "stress": 1},
                "result": "Aşçı ses çıkarmadı.",
            },
        ],
    }

  def ev_guard_bully(self, c):
    return {
        "title": "Muhafızın Kötü Muamelesi",
        "text": f"Muhafız {c.name}, görev yerinde seni sıkıştırıp küçük düşürmeye çalışıyor.",
        "options": [
            {
                "text": "Alttan al ve sessizce uzaklaş",
                "effects": {"stress": 10, "morale": -3},
                "result": "Gururun incindi ama zarar görmedin.",
            },
            {
                "text": "Gizli bir intikam planı yap",
                "effects": {"intrigue": 8, "stress": 5},
                "add_secret": f"{c.name}'in Zayıf Noktası",
                "result": "Ona gününü göstermeye yemin ettin.",
            },
            {
                "text": "Üstlerine şikayet et",
                "effects": {"personal_influence": -1, "stress": 3},
                "result": "Kimse pek önemsemedi.",
            },
        ],
    }

  def ev_noble_errand(self, c):
    return {
        "title": f"Gizli Görev: {c.name}",
        "text": f"{c.title} {c.name}, surların dışındaki karanlık bir kişiye gizli bir mektup ulaştırmanı istiyor.",
        "options": [
            {
                "text": "Mektubu güvenle ilet",
                "effects": {
                    "gold": 20,
                    "personal_influence": 3,
                    "stress": 4,
                },
                "result": "İşini başarıyla tamamlayıp altın kazandın.",
            },
            {
                "text": "Mektubu açıp sırrı öğren ve şantaj yap",
                "effects": {"intrigue": 15, "gold": 30, "stress": 10},
                "add_secret": f"{c.name}'in Karanlık Mektup Sırrı",
                "result": "Çok değerli bir koz elde ettin.",
            },
            {
                "text": "Görevi reddet",
                "effects": {"personal_influence": -3, "stress": -2},
                "result": "Tehlikeli işten uzak durdun.",
            },
        ],
    }

  def ev_cleaning_secret(self, c):
    return {
        "title": "Temizlik Sırasında Keşif",
        "text": f"Özel odaları temizlerken {c.name} tarafından düşürülmüş gizli muhasebe kayıtları buldun.",
        "options": [
            {
                "text": "Kayıtları kendi çıkarların için kullan",
                "effects": {"intrigue": 12, "gold": 20},
                "add_secret": f"{c.name}'in Gizli Hesap Kayıtları",
                "result": "Zenginlerin gizli hesaplarına ulaştın.",
            },
            {
                "text": "Görmezden gelip yerine koy",
                "effects": {"stress": -3},
                "result": "Başını belaya sokmadın.",
            },
        ],
    }

  def ev_stable_rumor(self, c):
    return {
        "title": "Ahırda Buluşma",
        "text": f"Ahırlarda {c.name} ile saray muhafızlarının gizli bir sevkiyat hakkında konuştuğunu duydun.",
        "options": [
            {
                "text": "Konuşulanları taşa kaz ve sakla (Sır Olarak Sakla)",
                "effects": {"intrigue": 10, "spy_network": 5},
                "add_secret": f"{c.name} ile Muhafızların Gizli Sevkiyatı",
                "result": "Casusluk ağın genişledi ve güçlü bir sır elde ettin.",
            },
            {
                "text": "Muhafızlara katılmak istediğini söyle",
                "effects": {"weapons": 10, "stress": 4},
                "result": "Sevkiyattan pay aldın.",
            },
        ],
    }

  def ev_guard_bribe(self, c):
    return {
        "title": "Kapıdaki Kaçakçılar",
        "text": f"Nöbetçi {c.name}, vergi ödemek istemeyen tüccarların rüşvet teklif ettiğini ve ne yapmanız gerektiğini soruyor.",
        "options": [
            {
                "text": "Rüşveti kabul edip parayı paylaşın",
                "effects": {"gold": 35, "stability": -4},
                "result": "Hazineye kayıtsız altın girdi.",
            },
            {
                "text": "Hepsini tutuklayıp adalete teslim et",
                "effects": {"stability": 8, "personal_influence": 3},
                "result": "Halk ve otorite memnun kaldı.",
            },
        ],
    }

  def ev_corridor_fight(self, c):
    return {
        "title": "Saray İçi Silahlı Arbede",
        "text": f"Muhafızlar ile saray hizmetkarları arasında {c.name} yüzünden kanlı bir kavga çıktı.",
        "options": [
            {
                "text": "Kılıcını çekip tarafları ayır",
                "effects": {"stability": 6, "health": -12, "morale": 5},
                "result": "Kavgayı bastırdın ama yaralandın.",
            },
            {
                "text": "Güvenli bir köşeden izle",
                "effects": {"stability": -8, "stress": 5},
                "result": "Ortalık savaş alanına döndü.",
            },
        ],
    }

  def ev_spy_whisper(self, c):
    return {
        "title": "Gölgedeki Casus",
        "text": f"Casus {c.name}, saraydaki en büyük açığın kimde olduğunu bildiğini ve karşılığında koruma istediğini söylüyor.",
        "options": [
            {
                "text": "Koruma sözü ver ve ağı kur",
                "effects": {"intrigue": 15, "spy_network": 15},
                "add_secret": f"{c.name}'in Casusluk İtirafı",
                "result": "Casus ağına katıldı.",
            },
            {
                "text": "Tehdit edip kov",
                "effects": {"intrigue": 5, "stress": 4},
                "result": "Uzaklaştırıldı.",
            },
        ],
    }

  def ev_noble_plot(self, c):
    return {
        "title": f"Soylu Komplosu: {c.name}",
        "text": f"{c.title} {c.name}, senin yükselişinden rahatsız ve altını oyuyor.",
        "options": [
            {
                "text": "Yüklü bir rüşvetle sustur",
                "effects": {"gold": -30, "intrigue": 8},
                "result": "Geçici olarak susmak zorunda kaldı.",
            },
            {
                "text": "Zindana attır",
                "effects": {"stability": -5, "personal_influence": 6},
                "result": "Karanlık hücreye gönderildi.",
                "imprison": c.id,
            },
            {
                "text": "Görmezden gel",
                "effects": {"stability": -10, "stress": 8},
                "result": "Komplo büyümeye devam ediyor.",
            },
        ],
    }

  def ev_gate_smuggler(self, c):
    return {
        "title": "Surlar Arasında Kaçakçılık",
        "text": f"{c.name} öncülüğünde sur arkasından yasaklı maddeler sokuluyor.",
        "options": [
            {
                "text": "Haraç kes ve ortak ol",
                "effects": {"gold": 40, "stability": -6},
                "result": "İyi para kazandın.",
            },
            {
                "text": "Malzemelere el koy",
                "effects": {"weapons": 15, "stability": 4},
                "result": "Sarayın savunması güçlendi.",
            },
        ],
    }

  def ev_weapon_shortage(self, c):
    return {
        "title": "Silah Deposu Krizi",
        "text": f"Muhafız komutanı {c.name}, depodaki kılıçların paslandığını ve acilen yenilenmesi gerektiğini bildiriyor.",
        "options": [
            {
                "text": "Hazineyi açıp demir satın al",
                "effects": {"gold": -25, "weapons": 20},
                "result": "Depolar yenilendi.",
            },
            {
                "text": "Eldekilerle idare etmelerini söyle",
                "effects": {"morale": -10, "stability": -4},
                "result": "Askerlerin morali bozuldu.",
            },
        ],
    }

  def ev_military_supply(self, c):
    return {
        "title": "Ordu Erzak Talebi",
        "text": f"General {c.name}, sınırdaki birlikler için acil erzak ve iaşe talep ediyor.",
        "options": [
            {
                "text": "Tüm talepleri karşıla",
                "effects": {"gold": -30, "food": -25, "morale": 15},
                "result": "Askerler sana minnettar.",
            },
            {
                "text": "Talebi yarı yarıya kes",
                "effects": {"gold": -15, "morale": -5},
                "result": "Birlikler homurdanıyor.",
            },
        ],
    }

  def ev_church_decree(self, c):
    return {
        "title": "Kutsal Ferman",
        "text": f"Başpiskopos {c.name}, halktan ek vergi toplanıp tapınağa aktarılmasını istiyor.",
        "options": [
            {
                "text": "Kilisenin isteğini kabul et",
                "effects": {"church": 20, "gold": 20, "people": -15},
                "result": "Rahipler seni dualarla andı.",
            },
            {
                "text": "Fermanı reddet",
                "effects": {"church": -25, "people": 10},
                "result": "Halk sevindi, kilise düşman oldu.",
            },
        ],
    }

  def ev_tax_evasion(self, c):
    return {
        "title": "Vergi Kaçakçılığı",
        "text": f"Tüccar {c.name}, hazineye vermesi gereken vergiyi eksik beyan ederken yakalandı.",
        "options": [
            {
                "text": "Tüm mal varlığına el koy",
                "effects": {"gold": 50, "merchants": -15},
                "result": "Hazine doldu, tüccarlar korktu.",
            },
            {
                "text": "Yarısını rüşvet olarak alıp serbest bırak",
                "effects": {"gold": 25, "intrigue": 5},
                "result": "Gizli anlaşma yapıldı.",
            },
        ],
    }

  def ev_court_brief(self, c):
    return {
        "title": "Yüksek Divan Raporu",
        "text": f"{c.name}, saraydaki tüm dengelerin senin elinde olduğunu ve dikkatli olman gerektiğini fısıldıyor.",
        "options": [
            {
                "text": "Gücünü pekiştir",
                "effects": {"personal_influence": 5, "stress": 3},
                "result": "Saraydaki ağırlığın arttı.",
            },
            {
                "text": "Gölgelerde kalmayı seç",
                "effects": {"intrigue": 8, "stress": -3},
                "result": "Dikkatleri üzerimden çektin.",
            },
        ],
    }

  def ev_diplomat_visit(self, c):
    return {
        "title": "Yabancı Elçi",
        "text": f"Komşu krallıktan gelen elçi {c.name}, gizli bir ittifak anlaşması teklif ediyor.",
        "options": [
            {
                "text": "Anlaşmayı imzala",
                "effects": {"stability": 10, "gold": 20, "intrigue": -5},
                "result": "Krallığın itibarı arttı.",
            },
            {
                "text": "Şüpheli bulup reddet",
                "effects": {"stress": 2},
                "result": "Elçi geri gönderildi.",
            },
        ],
    }

  def ev_assassination_attempt(self, c):
    return {
        "title": "Hayati Suikast Girişimi!",
        "text": f"Gece yarısı odana giren suikastçı, {c.name} tarafından gönderildiğini itiraf etti!",
        "options": [
            {
                "text": "Hemen idam et ve ibret-i alem yap",
                "effects": {"intrigue": 15, "health": -15, "stability": 5},
                "result": "Suikastçı ortadan kaldırıldı.",
                "eliminate": c.id,
            },
            {
                "text": "Zindana atıp konuştur",
                "effects": {"intrigue": 20, "health": -10},
                "result": "Hücrede sorguya çekiliyor.",
                "imprison": c.id,
            },
        ],
    }

  def ev_espionage_report(self, c):
    return {
        "title": "Kritik Casusluk Raporu",
        "text": f"Casus {c.name}, saraydaki en büyük hainin kim olduğunu gösteren belgeler ele geçirdi.",
        "options": [
            {
                "text": "Belgeleri şantaj için kullan",
                "effects": {"gold": 45, "intrigue": 15},
                "add_secret": f"{c.name} Tarafından Sunulan Hain Belgeleri",
                "result": "Servetine servet kattın.",
            },
            {
                "text": "Doğrudan krala sun",
                "effects": {"personal_influence": 10, "stability": 5},
                "result": "Takdir topladın.",
            },
        ],
    }

  def ev_coup_whisper(self, c):
    return {
        "title": "Darbe Fısıltıları",
        "text": f"{c.name}, tahtı ele geçirmek için mükemmel bir zaman olduğunu söylüyor.",
        "options": [
            {
                "text": "Hazırlıkları hızlandır",
                "effects": {"intrigue": 20, "stress": 10},
                "add_secret": f"{c.name} ile Darbe Planı Detayları",
                "result": "Darbe planı olgunlaşıyor.",
            },
            {
                "text": "Tehlikeli bulup reddet",
                "effects": {"stress": -5},
                "result": "Risk almaktan kaçındın.",
            },
        ],
    }

  def ev_treasury_crisis(self, c):
    return {
        "title": "Hazine Açığı Krizi",
        "text": f"Hazine yöneticisi {c.name}, kasalarda paranın tükendiğini ve acil önlem alınması gerektiğini bildiriyor.",
        "options": [
            {
                "text": "Halktan geçici savaş vergisi al",
                "effects": {"gold": 40, "people": -20},
                "result": "Kasa doldu ama halk öfkeli.",
            },
            {
                "text": "Saray harcamalarını kısı",
                "effects": {"stress": 8, "gold": 15},
                "result": "Kriz atlatıldı.",
            },
        ],
    }

  def ev_rebellion_scare(self, c):
    return {
        "title": "İsyan Çanı",
        "text": f"Şehir merkezinde {c.name} öncülüğünde ayaklanma provası yapıldığı duyuldu.",
        "options": [
            {
                "text": "Askerleri salıp dağıt",
                "effects": {"stability": 10, "people": -25, "weapons": -5},
                "result": "İsyan kanlı bastırıldı.",
            },
            {
                "text": "Halkın liderleriyle müzakere et",
                "effects": {"gold": -20, "people": 15, "stability": 5},
                "result": "Uzlaşma sağlandı.",
            },
        ],
    }

  def ev_church_schism(self, c):
    return {
        "title": "Kilise Bölünmesi",
        "text": f"Din adamları arasında {c.name} yüzünden büyük bir mezhep tartışması çıktı.",
        "options": [
            {
                "text": "Tarafını seçip bir grubu destekle",
                "effects": {"church": 15, "stability": -10},
                "result": "Kilisede ağırlık kazandın.",
            },
            {
                "text": "Tarafsız kalıp ikisini de uyar",
                "effects": {"stability": 5, "stress": 2},
                "result": "Dengeler korundu.",
            },
        ],
    }

  # ============================================================
  # 5. OYUN DÖNGÜSÜ, SEÇİM UYGULAMA VE KAYIT
  # ============================================================
  def execute_choice(self, opt):
    effects = opt.get("effects", {})
    for k, v in effects.items():
      if hasattr(self, k):
        setattr(self, k, getattr(self, k) + v)

    if "add_secret" in opt:
      s_text = opt["add_secret"]
      if s_text not in self.secrets:
        self.secrets.append(s_text)
        self.notifications.append(f"Yeni Sır Elde Edildi: {s_text}")

    if "imprison" in opt:
      c = self.get_character(opt["imprison"])
      if c:
        c.imprisoned = True
    if "eliminate" in opt:
      c = self.get_character(opt["eliminate"])
      if c:
        c.alive = False

    self.current_result = opt["result"]
    self.state = "RESULT"
    click_fx.play_win()

  def advance_time(self):
    self.day += 1
    self.hour = 8
    self.update_rank_and_progression()

    self.stress = max(0, self.stress - 2)
    self.health = min(100, self.health + 1)

    if self.day > self.max_days:
      self.state = "GAMEOVER"
      music_mgr.play("gameover")
      return

    self.generate_event()
    self.state = "PLAY"
    music_mgr.play("play")

  def save_game(self):
    data = {
        "day": self.day,
        "gold": self.gold,
        "stress": self.stress,
        "health": self.health,
        "rank": self.rank,
        "rank_level": self.rank_level,
        "personal_influence": self.personal_influence,
        "secrets": self.secrets,
    }
    try:
      with open(self.SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
      self.notifications.append("Oyun başarıyla kaydedildi!")
    except:
      pass


# ------------------------------------------------------------
# YARDIMCI ÇİZİM FONKSİYONLARI
# ------------------------------------------------------------
def draw_text(surface, text, font, color, x, y):
  obj = font.render(text, True, color)
  surface.blit(obj, (x, y))


def draw_button(surface, rect, text, bg_col, hover_col, text_col=TEXT):
  # Mouse pozisyonu artık sanal koordinat sistemine göre kontrol ediliyor
  virtual_mouse_pos = get_virtual_mouse_pos()
  is_hover = False
  if virtual_mouse_pos:
    is_hover = rect.collidepoint(virtual_mouse_pos)

  col = hover_col if is_hover else bg_col

  pygame.draw.rect(surface, col, rect, border_radius=10)
  pygame.draw.rect(surface, GOLD, rect, 2, border_radius=10)

  txt_obj = FONT.render(text, True, text_col)
  txt_rect = txt_obj.get_rect(
      center=(rect.x + rect.width // 2, rect.y + rect.height // 2)
  )
  surface.blit(txt_obj, txt_rect)
  return is_hover


# ------------------------------------------------------------
# DİNAMİK ÖLÇEKLENDİRME YARDIMCILARI
# ------------------------------------------------------------
def get_virtual_mouse_pos():
  actual_pos = pygame.mouse.get_pos()
  win_w, win_h = SCREEN.get_size()

  scale = min(win_w / INTERNAL_WIDTH, win_h / INTERNAL_HEIGHT)
  scaled_w = INTERNAL_WIDTH * scale
  scaled_h = INTERNAL_HEIGHT * scale

  offset_x = (win_w - scaled_w) / 2
  offset_y = (win_h - scaled_h) / 2

  mx, my = actual_pos
  if (
      offset_x <= mx <= offset_x + scaled_w
      and offset_y <= my <= offset_y + scaled_h
  ):
    vx = (mx - offset_x) / scale
    vy = (my - offset_y) / scale
    return int(vx), int(vy)
  return None


# ============================================================
# 6. ANA OYUN DÖNGÜSÜ
# ============================================================
def main():
  game = Game()
  music_mgr.play("menu")
  running = True
  tick = 0

  while running:
    tick += 1
    VIRTUAL_SCREEN.fill(BG_STONE)

    events = pygame.event.get()
    for event in events:
      if event.type == pygame.QUIT:
        running = False

      elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        v_pos = get_virtual_mouse_pos()
        if v_pos:
          click_fx.add_ripple(v_pos[0], v_pos[1])
          mx, my = v_pos

          if game.state == "MENU":
            if pygame.Rect(
                INTERNAL_WIDTH // 2 - 150, 400, 300, 50
            ).collidepoint((mx, my)):
              game.state = "PLAY"
              music_mgr.play("play")
            elif pygame.Rect(
                INTERNAL_WIDTH // 2 - 150, 470, 300, 50
            ).collidepoint((mx, my)):
              running = False

          elif game.state == "PLAY":
            tabs = [
                ("Olaylar", 50),
                ("Saray", 140),
                ("Entrika", 230),
                ("Fermanlar", 360),
                ("Profilim", 460),
            ]
            for t_name, t_x in tabs:
              if pygame.Rect(t_x, 20, 85, 35).collidepoint((mx, my)):
                if t_name == "Olaylar":
                  game.active_tab = "events"
                elif t_name == "Saray":
                  game.active_tab = "palace"
                elif t_name == "Entrika":
                  game.active_tab = "intrigue"
                elif t_name == "Fermanlar":
                  game.active_tab = "edicts"
                elif t_name == "Profilim":
                  game.active_tab = "profile"

            if pygame.Rect(INTERNAL_WIDTH - 120, 20, 100, 35).collidepoint(
                (mx, my)
            ):
              game.save_game()

            if game.active_tab == "events" and game.current_event:
              opts = game.current_event["options"]
              for i, opt in enumerate(opts):
                opt_rect = pygame.Rect(
                    INTERNAL_WIDTH // 2 - 350, 500 + i * 85, 700, 70
                )
                if opt_rect.collidepoint((mx, my)):
                  game.execute_choice(opt)

          elif game.state == "RESULT":
            cont_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 150, 600, 300, 50)
            if cont_rect.collidepoint((mx, my)):
              game.advance_time()

          elif game.state == "GAMEOVER":
            if pygame.Rect(INTERNAL_WIDTH // 2 - 150, 500, 300, 50).collidepoint(
                (mx, my)
            ):
              game = Game()
              game.state = "PLAY"
              music_mgr.play("play")

    # --- ÇİZİM AŞAMASI (VIRTUAL_SCREEN ÜZERİNE) ---
    if game.state == "MENU":
      draw_castle_walls(VIRTUAL_SCREEN, tick)
      draw_text(
          VIRTUAL_SCREEN,
          "ZALİM KRAL: TAHTIN GÖLGESİ",
          FONT_TITLE,
          GOLD,
          INTERNAL_WIDTH // 2 - 200,
          250,
      )
      draw_button(
          VIRTUAL_SCREEN,
          pygame.Rect(INTERNAL_WIDTH // 2 - 150, 400, 300, 50),
          "Oyuna Başla",
          PANEL_SOLID,
          PANEL_HOVER,
      )
      draw_button(
          VIRTUAL_SCREEN,
          pygame.Rect(INTERNAL_WIDTH // 2 - 150, 470, 300, 50),
          "Çıkış",
          PANEL_SOLID,
          PANEL_HOVER,
      )

    elif game.state == "PLAY":
      draw_castle_walls(VIRTUAL_SCREEN, tick)

      top_bar = pygame.Rect(30, 70, INTERNAL_WIDTH - 60, 50)
      pygame.draw.rect(VIRTUAL_SCREEN, PANEL_SOLID, top_bar, border_radius=8)
      pygame.draw.rect(VIRTUAL_SCREEN, GOLD, top_bar, 2, border_radius=8)
      info_str = (
          f"Rütbe: {game.rank} | Gün: {game.day}/{game.max_days} | Altın:"
          f" {game.gold} | Sağlık: {game.health} | Stres: {game.stress}/100"
      )
      draw_text(
          VIRTUAL_SCREEN, info_str, FONT, TEXT, top_bar.x + 20, top_bar.y + 15
      )

      tabs = [
          ("Olaylar", 50),
          ("Saray", 140),
          ("Entrika", 230),
          ("Fermanlar", 360),
          ("Profilim", 460),
      ]
      for t_name, t_x in tabs:
        col = (
            PANEL_HOVER if game.active_tab == t_name.lower()[:6] else PANEL_SOLID
        )
        draw_button(
            VIRTUAL_SCREEN,
            pygame.Rect(t_x, 20, 85, 35),
            t_name,
            col,
            PANEL_HOVER,
        )

      draw_button(
          VIRTUAL_SCREEN,
          pygame.Rect(INTERNAL_WIDTH - 120, 20, 100, 35),
          "Kaydet",
          PANEL_SOLID,
          PANEL_HOVER,
      )

      # --- SEKME İÇERİKLERİ ---
      if game.active_tab == "events" and game.current_event:
        ev_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 400, 150, 800, 320)
        pygame.draw.rect(VIRTUAL_SCREEN, PANEL_SOLID, ev_rect, border_radius=12)
        pygame.draw.rect(VIRTUAL_SCREEN, GOLD, ev_rect, 2, border_radius=12)

        draw_text(
            VIRTUAL_SCREEN,
            game.current_event["title"],
            FONT_BIG,
            GOLD,
            ev_rect.x + 30,
            ev_rect.y + 25,
        )
        draw_text(
            VIRTUAL_SCREEN,
            game.current_event["text"],
            FONT,
            TEXT,
            ev_rect.x + 30,
            ev_rect.y + 70,
        )

        if game.current_character:
          draw_character_card(
              VIRTUAL_SCREEN,
              INTERNAL_WIDTH // 2 + 50,
              170,
              game.current_character,
          )

        opts = game.current_event["options"]
        for i, opt in enumerate(opts):
          opt_rect = pygame.Rect(
              INTERNAL_WIDTH // 2 - 350, 500 + i * 85, 700, 70
          )
          draw_button(
              VIRTUAL_SCREEN,
              opt_rect,
              f"-> {opt['text']}",
              PANEL_2,
              PANEL_HOVER,
              GOLD_LIGHT,
          )

      elif game.active_tab == "palace":
        pal_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 400, 150, 800, 500)
        pygame.draw.rect(VIRTUAL_SCREEN, PANEL_SOLID, pal_rect, border_radius=12)
        pygame.draw.rect(VIRTUAL_SCREEN, GOLD, pal_rect, 2, border_radius=12)
        draw_text(
            VIRTUAL_SCREEN,
            "Saray Sakinleri ve Durumları",
            FONT_BIG,
            GOLD,
            pal_rect.x + 30,
            pal_rect.y + 25,
        )
        for idx, c in enumerate(game.characters[:8]):
          status = (
              "Zindanda"
              if c.imprisoned
              else ("Ölü" if not c.alive else "Görevde")
          )
          txt = f"{c.name} ({c.title}) - Sadakat: {c.loyalty} | Durum: {status}"
          draw_text(
              VIRTUAL_SCREEN,
              txt,
              FONT,
              TEXT,
              pal_rect.x + 30,
              pal_rect.y + 80 + idx * 40,
          )

      elif game.active_tab == "intrigue":
        intr_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 450, 150, 900, 500)
        pygame.draw.rect(
            VIRTUAL_SCREEN, PANEL_SOLID, intr_rect, border_radius=12
        )
        pygame.draw.rect(VIRTUAL_SCREEN, GOLD, intr_rect, 2, border_radius=12)

        draw_text(
            VIRTUAL_SCREEN,
            "Toplanan Gizli Bilgiler & Sırlar (Kozlar)",
            FONT_BIG,
            GOLD,
            intr_rect.x + 30,
            intr_rect.y + 25,
        )

        if not game.secrets:
          draw_text(
              VIRTUAL_SCREEN,
              "Henüz sarayda kimseye karşı kullanabileceğin bir sır"
              " toplamadın.",
              FONT,
              TEXT_DIM,
              intr_rect.x + 30,
              intr_rect.y + 80,
          )
        else:
          for idx, s in enumerate(game.secrets):
            draw_text(
                VIRTUAL_SCREEN,
                f"- {s} (Aktif Koz)",
                FONT,
                GOLD_LIGHT,
                intr_rect.x + 30,
                intr_rect.y + 80 + idx * 40,
            )

      elif game.active_tab == "edicts":
        ed_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 400, 150, 800, 500)
        pygame.draw.rect(VIRTUAL_SCREEN, PANEL_SOLID, ed_rect, border_radius=12)
        pygame.draw.rect(VIRTUAL_SCREEN, GOLD, ed_rect, 2, border_radius=12)
        draw_text(
            VIRTUAL_SCREEN,
            "Kraliyet Fermanları ve Yasalar",
            FONT_BIG,
            GOLD,
            ed_rect.x + 30,
            ed_rect.y + 25,
        )
        draw_text(
            VIRTUAL_SCREEN,
            "İlerleyen günlerde rütben arttıkça ferman çıkarabileceksin.",
            FONT,
            TEXT_DIM,
            ed_rect.x + 30,
            ed_rect.y + 80,
        )

      elif game.active_tab == "profile":
        prof_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 400, 150, 800, 450)
        pygame.draw.rect(
            VIRTUAL_SCREEN, PANEL_SOLID, prof_rect, border_radius=12
        )
        pygame.draw.rect(VIRTUAL_SCREEN, GOLD, prof_rect, 2, border_radius=12)
        draw_text(
            VIRTUAL_SCREEN,
            "Kişisel Durum & İstatistikler",
            FONT_BIG,
            GOLD,
            prof_rect.x + 30,
            prof_rect.y + 25,
        )
        draw_text(
            VIRTUAL_SCREEN,
            f"Mevcut Rütbe: {game.rank}",
            FONT,
            TEXT,
            prof_rect.x + 30,
            prof_rect.y + 80,
        )
        draw_text(
            VIRTUAL_SCREEN,
            f"Kişisel Etki/Güç: {game.personal_influence}",
            FONT,
            TEXT,
            prof_rect.x + 30,
            prof_rect.y + 120,
        )
        draw_text(
            VIRTUAL_SCREEN,
            f"Casus Ağı Gücü: {game.spy_network}",
            FONT,
            TEXT,
            prof_rect.x + 30,
            prof_rect.y + 160,
        )
        draw_text(
            VIRTUAL_SCREEN,
            f"Entrika Seviyesi: {game.intrigue}",
            FONT,
            TEXT,
            prof_rect.x + 30,
            prof_rect.y + 200,
        )

    elif game.state == "RESULT":
      draw_castle_walls(VIRTUAL_SCREEN, tick)
      res_rect = pygame.Rect(INTERNAL_WIDTH // 2 - 350, 250, 700, 300)
      pygame.draw.rect(VIRTUAL_SCREEN, PANEL_SOLID, res_rect, border_radius=12)
      pygame.draw.rect(VIRTUAL_SCREEN, GOLD, res_rect, 2, border_radius=12)

      draw_text(
          VIRTUAL_SCREEN,
          "Kararın Sonucu",
          FONT_TITLE,
          GOLD,
          res_rect.x + 30,
          res_rect.y + 30,
      )
      draw_text(
          VIRTUAL_SCREEN,
          game.current_result,
          FONT,
          TEXT,
          res_rect.x + 30,
          res_rect.y + 100,
      )
      draw_button(
          VIRTUAL_SCREEN,
          pygame.Rect(INTERNAL_WIDTH // 2 - 150, 600, 300, 50),
          "Devam Et",
          PANEL_2,
          PANEL_HOVER,
      )

    elif game.state == "GAMEOVER":
      draw_castle_walls(VIRTUAL_SCREEN, tick)
      draw_text(
          VIRTUAL_SCREEN,
          "OYUN BİTTİ — 90 GÜNÜ TAMAMLADIN",
          FONT_TITLE,
          RED,
          INTERNAL_WIDTH // 2 - 220,
          300,
      )
      draw_button(
          VIRTUAL_SCREEN,
          pygame.Rect(INTERNAL_WIDTH // 2 - 150, 500, 300, 50),
          "Yeniden Başla",
          PANEL_SOLID,
          PANEL_HOVER,
      )

    click_fx.update_and_draw(VIRTUAL_SCREEN)

    # --- GERÇEK EKRANA ÖLÇEKLEYEREK AKTARMA (SCALING & LETTERBOXING) ---
    SCREEN.fill((0, 0, 0))  # Kenar boşlukları için siyah zemin
    win_w, win_h = SCREEN.get_size()

    scale = min(win_w / INTERNAL_WIDTH, win_h / INTERNAL_HEIGHT)
    scaled_w = int(INTERNAL_WIDTH * scale)
    scaled_h = int(INTERNAL_HEIGHT * scale)

    offset_x = (win_w - scaled_w) // 2
    offset_y = (win_h - scaled_h) // 2

    scaled_surf = pygame.transform.smoothscale(
        VIRTUAL_SCREEN, (scaled_w, scaled_h)
    )
    SCREEN.blit(scaled_surf, (offset_x, offset_y))

    pygame.display.flip()
    CLOCK.tick(FPS)

  pygame.quit()
  sys.exit()


if __name__ == "__main__":
  main()