import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/tractor-ballast-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1").strip()
CUSTOM_TRACTOR = os.environ.get("CUSTOM_TRACTOR", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_tractors.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Tractor / Loader Model, Loader Lift @ Pivot Lbs, Bare Tractor Weight Lbs, Rear Tire Size, 75% Liquid Gal Per Tire, Hitch Category)
SEED_TRACTORS = [
    ("Kubota L2501 / L3301 / L3901 (LA525 / LA526 Loader)", 1131, 2623, "15-19.5 R4 / 11.2-24 R1", 22.0, "Category 1 (3-Point)"),
    ("Kubota BX2380 / BX2680 (LA344S Sub-Compact Loader)", 739, 1477, "26×12.00-12 R4/R14", 7.5, "Category 1 (Sub-Compact)"),
    ("Kubota BX23S Tractor Loader Backhoe (LA340 Loader)", 739, 1587, "26×12.00-12 R4/R14", 7.5, "Category 1 (Sub-Compact)"),
    ("Kubota B2601 / B2301 (LA435 Swift-Tach Loader)", 948, 1632, "12-16.5 R4 / 33×12.5-16.5", 13.5, "Category 1 (3-Point)"),
    ("Kubota LX2610 / LX3310 (LA535 Front-End Loader)", 1175, 1940, "15-19.5 R4 / 380/75R20 R14", 21.0, "Category 1 (3-Point)"),
    ("Kubota L4701 / L4802 (LA765 / LA766 Heavy Loader)", 1684, 3307, "17.5L-24 R4 / 13.6-24 R1", 36.0, "Category 1 / 2"),
    ("Kubota MX5400 / MX6000 (LA1065 Utility Loader)", 2275, 3759, "17.5L-24 R4 / 14.9-26 R1", 40.0, "Category 1 / 2"),
    ("John Deere 1025R Sub-Compact (120R Quik-Park Loader)", 758, 1560, "26×12.00-12 R4/R14", 7.5, "Category 1 (iMatch)"),
    ("John Deere 2025R / 2032R (220R Front-End Loader)", 1120, 1875, "12-16.5 R4 / 14-17.5 R4", 15.0, "Category 1 (iMatch)"),
    ("John Deere 3025E / 3032E / 3038E (300E Loader)", 1186, 2220, "15-19.5 R4 / 380/70R20 R14", 22.0, "Category 1 (iMatch)"),
    ("John Deere 3033R / 3039R / 3046R (320R Loader)", 1598, 2900, "15-19.5 R4 / 43×16.00-20", 24.0, "Category 1 (iMatch)"),
    ("John Deere 4044M / 4052M / 4066M (400E / 440R Loader)", 2509, 3770, "16.9-24 R4 / 13.6-28 R1", 42.0, "Category 1 / 2"),
    ("Kioti CK2610 / CK2620 / CK3510 (KL4030 Loader)", 1835, 2734, "15-19.5 R4 / 11.2-24 R1", 22.0, "Category 1 (3-Point)"),
    ("Kioti CX2510 Compact (KL2510 Front-End Loader)", 1092, 2198, "12-16.5 R4 Industrial", 13.5, "Category 1 (3-Point)"),
    ("Kioti DK4710SE / DK5310SE (KL5520 Heavy Loader)", 2474, 3585, "16.9-24 R4 Industrial", 38.0, "Category 1 / 2"),
    ("Kioti CS2210 / CS2520 Sub-Compact (SL2420 Loader)", 675, 1475, "26×12.00-12 R4/R14", 7.5, "Category 1 (Sub-Compact)"),
    ("TYM T25 / T254 Sub-Compact (TX25SL Front Loader)", 1380, 1797, "12-16.5 R4 Industrial", 13.5, "Category 1 (3-Point)"),
    ("TYM T474 / T494 / Branson 4820 (BL200 Loader)", 2196, 3699, "16.9-24 R4 Industrial", 38.0, "Category 1 / 2"),
    ("Mahindra Max 26XL / eMax 25L (26XL Loader)", 1402, 1865, "12-16.5 R4 Industrial", 13.5, "Category 1 (3-Point)"),
    ("Mahindra 1626 / 1635 / 1640 (1626L Loader)", 1560, 2458, "15-19.5 R4 Industrial", 22.0, "Category 1 (3-Point)"),
    ("Bobcat CT2025 / CT2035 / CT2040 (FL7 Front Loader)", 1369, 2711, "15-19.5 R4 Industrial", 22.0, "Category 1 (3-Point)"),
    ("New Holland Workmaster 25 & Boomer 35/40 Loader", 1500, 2650, "15-19.5 R4 Industrial", 22.0, "Category 1 (3-Point)"),
    ("Bad Boy 3026 & 4035 Compact Tractor Loader Sizing", 1590, 2860, "15-19.5 R4 Industrial", 22.0, "Category 1 (3-Point)"),
    ("5 Cu. Ft. Category 1 3-Point Hitch Steel Ballast Box Fill", 1250, 2500, "15-19.5 R4 Industrial", 22.0, "5.0 Cu Ft Concrete/Sand/Steel"),
    ("Titan Attachments vs Yitamotor 800-Lb 3-Point Ballast Box", 1200, 2400, "15-19.5 R4 Industrial", 22.0, "Category 1 Quick-Hitch Ready"),
    ("Rim Guard Beet Juice (11 lb/gal) vs Washer Fluid Tire Ballast", 1400, 2650, "15-19.5 R4 Industrial", 22.0, "Non-Corrosive Liquid Fill"),
    ("15-19.5 R4 & 11.2-24 R1 Tractor Tire Liquid Ballast Chart", 1350, 2600, "15-19.5 R4 (22 Gal/Tire)", 22.0, "75% Valve-Stem Level Fill"),
    ("26×12.00-12 & 12-16.5 Sub-Compact Tire Liquid Ballast", 850, 1650, "12-16.5 R4 (13.5 Gal/Tire)", 13.5, "75% Valve-Stem Level Fill"),
    ("17.5L-24 & 16.9-24 Utility Tractor Tire Liquid Ballast", 2100, 3600, "17.5L-24 R4 (36 Gal/Tire)", 36.0, "75% Valve-Stem Level Fill"),
    ("Clamp-On Pallet Forks Leverage Derating & Rear Ballast", 1200, 2500, "15-19.5 R4 Industrial", 22.0, "24\" Load Center Penalty")
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=1200.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_tractor_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Loader × Tire × Ballast Permutator.
    """
    discovered = []
    seeds = [
        "tractor ballast calculator ",
        "how much ballast for ",
        "kubota loader ballast ",
        "john deere ballast box "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "calculator" in pref or "how much" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        discovered.append((cleaned.title(), 1200, 2500, "15-19.5 R4 Industrial", 22.0, "Category 1 (3-Point)"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    loader_tiers = [
        (750, 1550, "750-Lb Sub-Compact Loader"),
        (1000, 1950, "1,000-Lb Small Compact Loader"),
        (1250, 2600, "1,250-Lb Standard Compact Loader"),
        (1650, 3100, "1,650-Lb Heavy Compact Loader"),
        (2200, 3750, "2,200-Lb Utility Tractor Loader"),
        (2800, 4400, "2,800-Lb Heavy Utility Loader")
    ]
    tire_configs = [
        ("26×12.00-12 Turf/R4 Tires", 7.5),
        ("12-16.5 R4 Industrial Tires", 13.5),
        ("15-19.5 R4 / 11.2-24 R1 Tires", 22.0),
        ("17.5L-24 / 16.9-24 R4 Tires", 38.0)
    ]
    for l_lift, t_wt, l_desc in loader_tiers:
        for tr_name, gal_t in tire_configs:
            combo_title = f"{l_desc} with {tr_name}"
            test_slug = slugify(f"{combo_title}-counterweight-ballast-calculator")
            if test_slug not in published_slugs:
                discovered.append((combo_title, l_lift, t_wt, tr_name, gal_t, "Category 1 (3-Point)"))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_tractor_data(tr_tuple):
    """
    LAPIS 3: Mesin Fisika Momen Tumpu Gardan Depan Traktor, 3-Point Ballast Box & 75% Tire Fill (100% Bebas Gagal).
    """
    model_name, loader_lbs, tractor_lbs, tire_spec, gal_per_tire, hitch_cat = tr_tuple

    # 1. Fisika Tumpuan Gardan Depan (Front Axle Fulcrum Physics):
    # Ketika loader mengangkat beban di ujung bucket (atau pallet forks), poros gardan depan menjadi titik tumpu (fulcrum) yang mengungkit roda belakang!
    # Tanpa pemberat 3-point hitch, beban gardan depan = ~1.55x dari berat angkat loader + 40% berat traktor.
    # Aturan ASABE / Kubota / John Deere:
    # Total Rear Counterweight (3-Point Hitch + Liquid Tire Ballast) = 1.00x hingga 1.15x dari Loader Lift Capacity:
    #   - 3-Point Hitch Ballast Box (mengungkit di belakang poros belakang, mengurangi beban gardan depan!) = ~65% - 75% dari Loader Lift
    #   - Liquid Rear Tire Ballast (menurunkan pusat gravitasi ke tanah, tetapi TIDAK mengurangi tekanan pada gardan depan) = ~35% - 45%
    rec_3pt_ballast_lbs = max(450, int(round(loader_lbs * 0.72, -1)))

    # 2. Berat Cairan Ban Belakang (Pair of 2 Rear Tires @ 75% Valve-Stem Fill):
    total_liquid_gal_pair = round(gal_per_tire * 2.0, 1)
    # Beet Juice / Rim Guard = 10.7 - 11.0 lbs/gal; Windshield Washer Fluid / RV Antifreeze = 8.4 lbs/gal
    beet_juice_pair_lbs = int(round(total_liquid_gal_pair * 10.8))
    washer_fluid_pair_lbs = int(round(total_liquid_gal_pair * 8.4))

    total_combined_ballast_lbs = rec_3pt_ballast_lbs + beet_juice_pair_lbs

    # 3. Perhitungan Volume & Isi Kotak Pemberat 3-Point Hitch (Standar 5.0 Cu. Ft. Steel Box = 135 lbs kosong):
    box_empty_lbs = 135
    fill_weight_needed_lbs = max(300, rec_3pt_ballast_lbs - box_empty_lbs)
    # Densitas Material Pengisi:
    # - Beton Cor (Ready-Mix Concrete) = 150 lbs/cu. ft. (1 kantong 80-lb Sakrete = 0.60 cu. ft.)
    # - Pasir Kering / Kerikil (Pea Gravel/Sand) = 105 lbs/cu. ft.
    # - Campuran Beton + Besi Tua/Barbel (Concrete + Steel Scrap) = 220 lbs/cu. ft.
    concrete_bags_80lb = max(5, int(math.ceil(fill_weight_needed_lbs / 80.0)))
    concrete_box_total_lbs = box_empty_lbs + (concrete_bags_80lb * 80)

    # 4. Kapasitas Angkat Aman dengan Clamp-On Pallet Forks (24-Inch Load Center Derating = ~58% dari Pivot Pin Capacity):
    pallet_fork_safe_lbs = int(round(loader_lbs * 0.58, -1))

    return {
        "tractor_name": model_name,
        "hitch_category": hitch_cat,
        "seo_title": f"{model_name} Rear Ballast Box, Tire Liquid & Counterweight Calculator (2026)",
        "meta_description": f"Calculate exact 3-point hitch ballast box weight ({rec_3pt_ballast_lbs:,} lbs / {concrete_bags_80lb} bags concrete), 75% rear tire liquid fill ({total_liquid_gal_pair} gal = {beet_juice_pair_lbs} lbs Beet Juice), and {pallet_fork_safe_lbs}-lb pallet fork capacity for {model_name}.",
        "specs": {
            "loader_lift_pivot_lbs": loader_lbs,
            "bare_tractor_weight_lbs": tractor_lbs,
            "recommended_3pt_ballast_lbs": rec_3pt_ballast_lbs,
            "rear_tire_size_spec": tire_spec,
            "liquid_gallons_pair": total_liquid_gal_pair,
            "beet_juice_weight_pair_lbs": beet_juice_pair_lbs,
            "washer_fluid_weight_pair_lbs": washer_fluid_pair_lbs,
            "total_combined_ballast_lbs": total_combined_ballast_lbs,
            "concrete_80lb_bags_needed": concrete_bags_80lb,
            "pallet_fork_24in_safe_lbs": pallet_fork_safe_lbs,
            "hitch_category": hitch_cat
        },
        "fulcrum_verdict": f"With a front-end loader lift rating of {loader_lbs:,} lbs at the pivot pins (~{pallet_fork_safe_lbs:,} lbs at a 24-inch pallet fork load center) on a {tractor_lbs:,}-lb chassis, {model_name} uses the front axle as a lever fulcrum that unweights the rear tires during heavy bucket breakout. To relieve front-axle bevel-gear stress and prevent rear-wheel tip-up, hang {rec_3pt_ballast_lbs:,} lbs on the {hitch_cat} 3-point hitch (a 135-lb steel ballast box filled with {concrete_bags_80lb}× 80-lb bags of concrete = {concrete_box_total_lbs:,} lbs) AND fill both {tire_spec} rear tires to 75% valve-stem level ({total_liquid_gal_pair} total gallons = +{beet_juice_pair_lbs} lbs of non-corrosive Beet Juice or +{washer_fluid_pair_lbs} lbs of -20°F Washer Fluid), yielding {total_combined_ballast_lbs:,} lbs of combined stability.",
        "hardware_bundle": [
            {
                "badge": f"800-Lb {hitch_cat.split()[0]} Cat-1 Ballast Box",
                "title": "Heavy-Duty Category 1 3-Point Hitch 800-Lb Steel Ballast Box w/ 2\" Receiver Hitch & Tool Tubes",
                "price_range": "$219 - $369",
                "amazon_query": "Category 1 3 Point Hitch Ballast Box 800 lb Tractor Counterweight Receiver",
                "tr_note": f"Holds 5.0+ cu. ft. of concrete, sand, or steel ({rec_3pt_ballast_lbs:,}+ lbs) behind the rear axle to unload front-axle bearings."
            },
            {
                "badge": "Cat-1 3-Point Quick Hitch",
                "title": "Category 1 3-Point Quick Hitch Adapter (3,000 Lb Capacity) + Top-Link Pin & Bushing Kit",
                "price_range": "$139 - $249",
                "amazon_query": "Category 1 3 Point Quick Hitch Tractor Adapter Bushing Kit",
                "tr_note": "Adds 70 lbs of permanent rear weight and lets you hook up your 800-lb ballast box from the tractor seat in 10 seconds."
            },
            {
                "badge": f"{pallet_fork_safe_lbs * 2:,} Lb Loader Pallet Forks",
                "title": "Heavy-Duty Clamp-On / Quick-Attach Loader Bucket Pallet Forks w/ Adjustable Stabilizer Bar & Grab Hooks",
                "price_range": "$149 - $359",
                "amazon_query": "Tractor Loader Bucket Clamp On Pallet Forks Stabilizer Bar Grab Hooks",
                "tr_note": f"Anti-rollover stabilizer bar keeps forks parallel when lifting {pallet_fork_safe_lbs:,}-lb logs, brush, and pallets."
            },
            {
                "badge": "Tire Liquid Fill Kit & Spacers",
                "title": "Brass Air-Water Tractor Tire Ballast Fill Valve Adapter + Self-Priming Transfer Pump & Wheel Spacers",
                "price_range": "$39 - $229",
                "amazon_query": "Tractor Tire Air Water Ballast Fill Adapter Valve Kit Transfer Pump",
                "tr_note": f"Threads directly onto coreless valve stems to pump {total_liquid_gal_pair} gallons into your rear tires while venting trapped air."
            }
        ],
        "operator_checklist": [
            f"Understand Why Liquid Tire Ballast Alone Is NOT Enough: {beet_juice_pair_lbs} lbs of fluid inside your {tire_spec} rear tires rests directly on the ground and prevents tipping, but it adds ZERO leverage behind the rear axle to take weight off your front axle! You MUST hang {rec_3pt_ballast_lbs:,} lbs on the 3-point hitch so the rear axle acts as a seesaw fulcrum that lifts weight off the fragile front axle.",
            "Fill Rear Tires to the 75% Valve-Stem Level (10-o'clock or 2-o'clock position), NEVER 100% full: a tire needs a 25% compressible air cushion at the top to absorb stump/rock impacts without bursting the sidewall.",
            "Use Rim Guard (Beet Juice — 11.0 lbs/gal, freeze-proof to -35°F), -20°F Windshield Washer Fluid (8.4 lbs/gal), or Propylene Glycol RV Antifreeze—NEVER use raw Calcium Chloride salt without inner tubes, as salt water rots steel rims from the inside out.",
            "Before pouring concrete into your 3-Point Steel Ballast Box, stand two या three 2-inch PVC pipes vertically inside the box (capped at the bottom with a 1/4\" drain hole) to create built-in holsters for shovels, rakes, and chainsaws, and embed a 2\" receiver tube or lifting eye."
        ],
        "faqs": [
            {
                "q": f"How much rear ballast do I need for {model_name} ({loader_lbs:,} lb loader)?",
                "a": f"To safely lift {loader_lbs:,} lbs at the loader pivot pins without overloading the front axle or lifting a rear tire on uneven ground, hang {rec_3pt_ballast_lbs:,} lbs on the 3-point hitch (approx. 70%–75% of loader capacity) AND fill both rear tires with {total_liquid_gal_pair} gallons of liquid ballast (+{beet_juice_pair_lbs} lbs Beet Juice or +{washer_fluid_pair_lbs} lbs Washer Fluid)."
            },
            {
                "q": f"How many 80-lb bags of concrete fit inside a 3-point ballast box for {rec_3pt_ballast_lbs:,} lbs?",
                "a": f"A standard Category 1 steel ballast box weighs ~135 lbs empty and holds ~5.0 to 5.3 cubic feet. Adding {concrete_bags_80lb} bags of 80-lb ready-mix concrete (+{concrete_bags_80lb * 80} lbs) brings the total 3-point hitch counterweight to {concrete_box_total_lbs:,} lbs."
            },
            {
                "q": f"How much can {model_name} lift with clamp-on pallet forks?",
                "a": f"Manufacturer loader ratings ({loader_lbs:,} lbs) are measured at the bucket pivot pins. Because clamp-on pallet forks shift the load's center of gravity 24 inches forward of the bucket edge, safe lifting capacity is ~58% of pivot capacity = {pallet_fork_safe_lbs:,} lbs (with full rear ballast attached)."
            }
        ]
    }


def generate_tractor_data(tr_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_tractor_data(tr_tuple)

    model_name, loader_lbs, tractor_lbs, tire_spec, gal_per_tire, hitch_cat = tr_tuple
    det_fallback = build_deterministic_tractor_data(tr_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified ASABE Agricultural Equipment Engineer & Compact Tractor Loader Stability Specialist. Create an accurate 2026 front-end loader counterweight, 3-point hitch ballast box density, front-axle fulcrum relief, and 75% rear tire liquid ballast guide for: "{model_name}".
Baseline specs: Loader Lift @ Pivot={loader_lbs} lbs (24" Pallet Fork Safe Lift={sp['pallet_fork_24in_safe_lbs']} lbs), Bare Tractor Weight={tractor_lbs} lbs, Recommended 3-Point Ballast Box={sp['recommended_3pt_ballast_lbs']} lbs ({sp['concrete_80lb_bags_needed']}x 80-lb Concrete Bags), Rear Tires={tire_spec} ({sp['liquid_gallons_pair']} Gal Total Pair = +{sp['beet_juice_weight_pair_lbs']} lbs Beet Juice / +{sp['washer_fluid_weight_pair_lbs']} lbs Washer Fluid), Hitch={hitch_cat}.
Return ONLY a valid JSON object matching this exact schema:
{{
  "tractor_name": "{model_name}",
  "hitch_category": "{hitch_cat}",
  "seo_title": "{model_name} Rear Ballast Box, Tire Liquid & Counterweight Calculator (2026)",
  "meta_description": "Calculate exact 3-point hitch ballast box weight, 80-lb concrete bag count, 75% rear tire liquid ballast gallons, and pallet fork lift capacity for {model_name}.",
  "specs": {{
    "loader_lift_pivot_lbs": {loader_lbs},
    "bare_tractor_weight_lbs": {tractor_lbs},
    "recommended_3pt_ballast_lbs": {sp['recommended_3pt_ballast_lbs']},
    "rear_tire_size_spec": "{tire_spec}",
    "liquid_gallons_pair": {sp['liquid_gallons_pair']},
    "beet_juice_weight_pair_lbs": {sp['beet_juice_weight_pair_lbs']},
    "washer_fluid_weight_pair_lbs": {sp['washer_fluid_weight_pair_lbs']},
    "total_combined_ballast_lbs": {sp['total_combined_ballast_lbs']},
    "concrete_80lb_bags_needed": {sp['concrete_80lb_bags_needed']},
    "pallet_fork_24in_safe_lbs": {sp['pallet_fork_24in_safe_lbs']},
    "hitch_category": "{hitch_cat}"
  }},
  "fulcrum_verdict": "3-sentence technical summary stating loader pivot vs pallet fork capacity, required 3-point hitch ballast box weight in lbs (and 80-lb concrete bags), and 75% rear tire liquid gallons/weight.",
  "hardware_bundle": [
    {{
      "badge": "800-Lb Cat-1 Ballast Box",
      "title": "Heavy-Duty Category 1 3-Point Hitch 800-Lb Steel Ballast Box w/ 2\" Receiver",
      "price_range": "$219 - $369",
      "amazon_query": "Category 1 3 Point Hitch Ballast Box 800 lb Tractor Counterweight",
      "tr_note": "1-sentence rear-axle fulcrum leverage and front-axle relief note"
    }},
    {{
      "badge": "Cat-1 3-Point Quick Hitch",
      "title": "Category 1 3-Point Quick Hitch Adapter (3,000 Lb) + Bushing Kit",
      "price_range": "$139 - $249",
      "amazon_query": "Category 1 3 Point Quick Hitch Tractor Adapter Bushing Kit",
      "tr_note": "1-sentence fast hookup and extra rear weight note"
    }},
    {{
      "badge": "Loader Bucket Pallet Forks",
      "title": "Heavy-Duty Clamp-On Loader Bucket Pallet Forks w/ Stabilizer Bar & Grab Hooks",
      "price_range": "$149 - $359",
      "amazon_query": "Tractor Loader Bucket Clamp On Pallet Forks Stabilizer Bar",
      "tr_note": "1-sentence 24-inch load center and stabilizer bar note"
    }},
    {{
      "badge": "Tire Liquid Fill Adapter Kit",
      "title": "Brass Air-Water Tractor Tire Ballast Fill Valve Adapter + Transfer Pump",
      "price_range": "$39 - $229",
      "amazon_query": "Tractor Tire Air Water Ballast Fill Adapter Valve Kit Pump",
      "tr_note": "1-sentence 75% valve-stem fill and air-bleed note"
    }}
  ],
  "operator_checklist": [
    "Step 1 regarding why 3-point hitch ballast unloads the front axle while tire liquid only lowers center of gravity",
    "Step 2 regarding 75% valve-stem level tire fill (leaving 25% air cushion)",
    "Step 3 regarding Beet Juice (11 lb/gal) vs -20F Washer Fluid (8.4 lb/gal) vs corrosive calcium",
    "Step 4 regarding embedding PVC tool holsters before pouring concrete into the ballast box"
  ],
  "faqs": [
    {{"q": "How much rear ballast weight do I need for {model_name}?", "a": "Exact 3-point hitch lbs plus rear tire liquid gallons and lbs."}},
    {{"q": "How many gallons of Beet Juice or Washer Fluid go into {tire_spec} tires?", "a": "Exact gallons per tire and per pair at 75% fill, with exact lbs added."}},
    {{"q": "How much weight fits in a 5 cu ft 3-point ballast box with sand vs concrete vs steel?", "a": "Exact total weight comparison for dry sand (660 lbs), concrete (885 lbs), and steel/concrete mix (1,200+ lbs)."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{model_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")
                break

    return det_fallback


def build_tractor_html_page(data, slug, mon_cfg):
    tr_name = data.get("tractor_name", "Compact Tractor Loader Counterweight")
    sp = data.get("specs", {})
    ldr_lbs = int(safe_float(sp.get("loader_lift_pivot_lbs", 1200), 1200))
    tr_lbs = int(safe_float(sp.get("bare_tractor_weight_lbs", 2500), 2500))
    box_lbs = int(safe_float(sp.get("recommended_3pt_ballast_lbs", 860), 860))
    tire_s = sp.get("rear_tire_size_spec", "15-19.5 R4 Industrial")
    gal_pair = round(safe_float(sp.get("liquid_gallons_pair", 44.0), 44.0), 1)
    beet_lbs = int(safe_float(sp.get("beet_juice_weight_pair_lbs", 475), 475))
    wash_lbs = int(safe_float(sp.get("washer_fluid_weight_pair_lbs", 370), 370))
    tot_bal = int(safe_float(sp.get("total_combined_ballast_lbs", 1335), 1335))
    bags_80 = int(safe_float(sp.get("concrete_80lb_bags_needed", 9), 9))
    fork_lbs = int(safe_float(sp.get("pallet_fork_24in_safe_lbs", 700), 700))

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "3+Point+Hitch+Ballast+Box+Category+1+Quick+Hitch"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{tr_name} 3-Point Ballast Box & Tire Liquid Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "3 Point Hitch Ballast Box")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-orange-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-orange-500/10 text-orange-400 border border-orange-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Tractor Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$69+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">🚜 {item.get('tr_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Rear Tractor Tire Size vs 75% Liquid Gallons & Added Weight Reference Matrix Table
    tire_tiers = [
        ("26×12.00-12 (Sub-Compact BX/1025R)", "15.0 Gal (7.5 Gal/Tire)", "+162 lbs (Pair)", "+126 lbs (Pair)", "550–650 lb 3-Pt Box"),
        ("12-16.5 R4 (Compact B2601/2025R)", "27.0 Gal (13.5 Gal/Tire)", "+292 lbs (Pair)", "+227 lbs (Pair)", "700–800 lb 3-Pt Box"),
        ("14-17.5 R4 (Mid-Compact 2032R)", "33.0 Gal (16.5 Gal/Tire)", "+356 lbs (Pair)", "+277 lbs (Pair)", "800–900 lb 3-Pt Box"),
        ("15-19.5 R4 (Standard L2501/3032E)", "44.0 Gal (22.0 Gal/Tire)", "+475 lbs (Pair)", "+370 lbs (Pair)", "850–1,050 lb 3-Pt Box"),
        ("11.2-24 R1 Ag (Standard Ag Tire)", "48.0 Gal (24.0 Gal/Tire)", "+518 lbs (Pair)", "+403 lbs (Pair)", "900–1,100 lb 3-Pt Box"),
        ("17.5L-24 R4 (Utility L4701/MX5400)", "72.0 Gal (36.0 Gal/Tire)", "+778 lbs (Pair)", "+605 lbs (Pair)", "1,200–1,600 lb 3-Pt")
    ]
    matrix_rows_html = ""
    for t_lbl, g_lbl, b_lbl, w_lbl, bx_lbl in tire_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{t_lbl}</td>
          <td class="py-3 px-4 text-zinc-300">{g_lbl}</td>
          <td class="py-3 px-4 font-bold text-orange-400">{b_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{w_lbl}</td>
          <td class="py-3 px-4 text-xs text-zinc-300">{bx_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("operator_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-orange-500 rounded cursor-pointer tr-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>ASABE Safety Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', tr_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', tr_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-orange-500 text-zinc-950 px-2 py-0.5 rounded font-black">TRACTOR</span>BallastIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop 3-Point Ballast Boxes & Hitches →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-orange-500 text-zinc-950 px-3 py-1 rounded-full">3-Pt Box: {box_lbs:,} lbs ({bags_80} Bags Concrete)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Tires: {gal_pair:g} Gal (+{beet_lbs} lbs Beet Juice)</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">Loader: {ldr_lbs:,} lbs (Forks: {fork_lbs:,} lbs)</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', tr_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-orange-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>ASABE Front-Axle Fulcrum & Counterweight Verdict:</strong> {data.get('fulcrum_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE 3-POINT BALLAST BOX, TIRE LIQUID & PALLET FORK CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {tr_name} Ballast Box & Tire Liquid Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Adjust your front-end loader lift capacity, rear tire size, liquid ballast fluid type, and ballast box fill material to compute exact 3-point counterweight lbs, concrete bags needed, and safe pallet fork load.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="ldrSlider" class="text-zinc-300">Front-End Loader Max Lift @ Pivot Pins (Lbs)</label>
              <span class="text-orange-400 font-bold"><span id="ldrVal">{ldr_lbs:,}</span> lbs</span>
            </div>
            <input id="ldrSlider" type="range" min="500" max="3200" step="50" value="{ldr_lbs}" class="w-full accent-orange-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="tireSelect" class="block text-xs font-medium text-zinc-400 mb-1">Rear Tire Size (75% Fill Gal)</label>
              <select id="tireSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="15.0" {"selected" if gal_pair <= 18 else ""}>26×12.00-12 (15 Gal Pair)</option>
                <option value="27.0" {"selected" if 18 < gal_pair <= 32 else ""}>12-16.5 R4 (27 Gal Pair)</option>
                <option value="44.0" {"selected" if 32 < gal_pair <= 52 else ""}>15-19.5 R4 / 11.2-24 (44 Gal Pair)</option>
                <option value="72.0" {"selected" if gal_pair > 52 else ""}>17.5L-24 / 16.9-24 (72 Gal Pair)</option>
              </select>
            </div>
            <div>
              <label for="fluidSelect" class="block text-xs font-medium text-zinc-400 mb-1">Liquid Tire Ballast Fluid</label>
              <select id="fluidSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="10.8|Beet Juice" selected>Beet Juice / Rim Guard (10.8 lb/gal)</option>
                <option value="8.4|Washer Fluid">-20°F Washer / RV Fluid (8.4 lb/gal)</option>
              </select>
            </div>
          </div>

          <div>
            <label for="boxFillSelect" class="block text-xs font-medium text-zinc-400 mb-1">5.2 Cu. Ft. 3-Point Steel Ballast Box Fill Material</label>
            <select id="boxFillSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
              <option value="105|Dry Sand / Pea Gravel">Dry Sand or Pea Gravel (105 lb/ft³ → ~680 lbs Total)</option>
              <option value="150|Ready-Mix Concrete" selected>Ready-Mix Concrete (150 lb/ft³ → ~915 lbs Total)</option>
              <option value="225|Concrete + Steel Scrap">Concrete + Steel Scrap/Plates (225 lb/ft³ → ~1,300 lbs)</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-orange-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-orange-400 font-bold">Required 3-Point Box</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="boxLbsOut">{box_lbs:,}</span> <span class="text-xs font-normal text-zinc-400">lbs</span></div>
            <p id="bagsNoteOut" class="text-xs text-orange-400 font-semibold mt-1">{bags_80} × 80-lb Concrete Bags</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">75% Tire Liquid + Forks</span>
            <div class="text-2xl sm:text-3xl font-black text-emerald-400 mt-1">+<span id="tireLbsOut">{beet_lbs}</span> <span class="text-xs font-normal text-zinc-400">lbs</span></div>
            <p id="forkNoteOut" class="text-xs text-zinc-300 font-semibold mt-1">Safe Pallet Forks: {fork_lbs:,} lbs</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-orange-950/40 border border-orange-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="trAdviceBanner" class="text-sm text-orange-100 font-medium"></div>
        <a id="dynamicTrBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched 3-Point Ballast Box & Quick Hitch on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {tr_name} Ballast Box, Quick Hitch & Fork Bundle</h2>
        <span class="text-xs text-zinc-400">ASABE Category 1 Standard & Rollover-Protected</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Tractor Rear Tire Size, 75% Liquid Gallons, Beet Juice vs. Washer Fluid & 3-Point Box Chart</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">Rear Tire Size & Class</th>
              <th class="py-3.5 px-4">75% Liquid Volume</th>
              <th class="py-3.5 px-4 text-orange-400">Beet Juice (10.8 lb/gal)</th>
              <th class="py-3.5 px-4 text-emerald-400">Washer Fluid (8.4 lb/gal)</th>
              <th class="py-3.5 px-4">Matched 3-Point Ballast</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">ASABE Tractor Loader Fulcrum, 75% Tire Fill & Ballast Box Checklist</h2>
        <span id="trBadge" class="text-xs font-bold bg-zinc-800 text-orange-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({tr_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} TractorBallastIndex. Independent Compact Tractor Loader Counterweight & Tire Ballast Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const ldrSlider = document.getElementById('ldrSlider');
    const tireSelect = document.getElementById('tireSelect');
    const fluidSelect = document.getElementById('fluidSelect');
    const boxFillSelect = document.getElementById('boxFillSelect');
    const ldrVal = document.getElementById('ldrVal');
    const boxLbsOut = document.getElementById('boxLbsOut');
    const bagsNoteOut = document.getElementById('bagsNoteOut');
    const tireLbsOut = document.getElementById('tireLbsOut');
    const forkNoteOut = document.getElementById('forkNoteOut');
    const trAdviceBanner = document.getElementById('trAdviceBanner');
    const dynamicTrBtn = document.getElementById('dynamicTrBtn');

    function recalculateTractor() {{
      const ldrLbs = parseInt(ldrSlider.value, 10);
      const galPair = parseFloat(tireSelect.value);
      const fluidParts = fluidSelect.value.split('|');
      const lbPerGal = parseFloat(fluidParts[0]);
      const fluidName = fluidParts[1];
      const fillParts = boxFillSelect.value.split('|');
      const fillDensity = parseInt(fillParts[0], 10);

      ldrVal.textContent = ldrLbs.toLocaleString();

      const req3PtLbs = Math.max(450, Math.round((ldrLbs * 0.72) / 10) * 10);
      const fillNeededLbs = Math.max(300, req3PtLbs - 135);
      const bags80 = Math.max(5, Math.ceil(fillNeededLbs / 80.0));
      const reqBoxCuFt = (fillNeededLbs / fillDensity).toFixed(1);

      const tireAddedLbs = Math.round(galPair * lbPerGal);
      const safeForkLbs = Math.round((ldrLbs * 0.58) / 10) * 10;

      boxLbsOut.textContent = req3PtLbs.toLocaleString();
      bagsNoteOut.textContent = `${{bags80}} × 80-lb Bags (~${{reqBoxCuFt}} ft³ Fill)`;
      tireLbsOut.textContent = tireAddedLbs.toLocaleString();
      forkNoteOut.textContent = `Safe Pallet Forks: ${{safeForkLbs.toLocaleString()}} lbs`;

      trAdviceBanner.innerHTML = `🚜 <strong>ASABE Counterweight Spec:</strong> A ${{ldrLbs.toLocaleString()}}-lb loader requires a <strong>Category 1 3-Point Hitch Steel Ballast Box (${{req3PtLbs.toLocaleString()}} lbs = ${{bags80}} bags concrete)</strong> + <strong>Category 1 Quick Hitch</strong> + <strong>${{galPair}} Gal of ${{fluidName}} (+${{tireAddedLbs}} lbs)</strong> in the rear tires.`;
      dynamicTrBtn.href = `https://${{amzDomain}}/s?k=Category+1+3+Point+Hitch+Ballast+Box+800+lb+Quick+Hitch+Tractor+Tire+Fill+Valve&tag=${{amzTag}}`;
    }}

    ldrSlider.addEventListener('input', recalculateTractor);
    tireSelect.addEventListener('change', recalculateTractor);
    fluidSelect.addEventListener('change', recalculateTractor);
    boxFillSelect.addEventListener('change', recalculateTractor);
    recalculateTractor();

    const checks = document.querySelectorAll('.tr-check');
    const badge = document.getElementById('trBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "3+Point+Hitch+Ballast+Box+Category+1+Quick+Hitch"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-orange-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-orange-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('box_lbs', 850):,} lb 3-Pt Box</span>
            <span class="text-xs text-zinc-400">Tires: {item.get('gal_pair', 44):g} Gal (+{item.get('beet_lbs', 475)} lb)</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-orange-400 transition">{item['tractor_name']}</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-orange-400">Calculate 3-Pt Ballast & Tire Liquid →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TractorBallastIndex — Compact Tractor 3-Point Ballast Box & Tire Liquid Weight Calculator (2026)</title>
  <meta name="description" content="Calculate exact compact tractor front-end loader counterweight, Category 1 3-point hitch ballast box concrete/sand weight, and 75% rear tire liquid ballast gallons for Kubota, John Deere, Kioti, TYM, and Mahindra tractors.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="TractorBallastIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-orange-500 text-zinc-950 px-2 py-0.5 rounded font-black">TRACTOR</span>BallastIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop 3-Point Ballast Boxes & Hitches →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Tractor Loader Counterweight, 3-Point Ballast Box & Tire Liquid Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your compact tractor model, loader rating, or rear tire size below to calculate 3-point hitch ballast box concrete bags, 75% rear tire Beet Juice / Washer Fluid gallons, and pallet fork lift limits.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search tractor model or tire size (e.g. Kubota L2501, BX2380, John Deere 1025R, 3032E, Kioti CK2610, 15-19.5 R4...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-orange-500">
      </div>
    </div>

    <div id="trGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} TractorBallastIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('trGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>TractorBallastIndex Compact Tractor Loader Counterweight & Tire Ballast Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Compact Tractor 3-Point Hitch Ballast Box & 75% Liquid Tire Ballast Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_TRACTOR:
        candidates.append((CUSTOM_TRACTOR.strip(), 1200, 2500, "15-19.5 R4 Industrial", 22.0, "Category 1 (3-Point)"))
    candidates.extend(SEED_TRACTORS)
    candidates.extend(discover_google_tractor_queries(published_slugs))

    new_urls = []
    count = 0

    for tr_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        t_name = tr_tuple[0]
        slug = slugify(f"{t_name}-counterweight-ballast-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating tractor 3-point ballast & tire liquid calculator for: {t_name}...")
        try:
            data = generate_tractor_data(tr_tuple)
            build_tractor_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "tractor_name": data.get("tractor_name", t_name),
                "slug": slug,
                "title": data.get("seo_title", f"{t_name} Ballast Calculator"),
                "description": data.get("meta_description", ""),
                "box_lbs": int(safe_float(sp.get("recommended_3pt_ballast_lbs", 860), 860)),
                "gal_pair": round(safe_float(sp.get("liquid_gallons_pair", tr_tuple[4] * 2.0), 44.0), 1),
                "beet_lbs": int(safe_float(sp.get("beet_juice_weight_pair_lbs", 475), 475)),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {t_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new compact tractor counterweight & tire ballast calculator pages.")


if __name__ == "__main__":
    main()
