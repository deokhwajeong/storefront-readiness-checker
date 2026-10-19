"""Generate the synthetic sample catalog in data/catalog.yaml.

Every app, partner, and string here is fictional. The catalog is generated
rather than hand-edited so that the deliberate defects ("seeded issues") are
listed in one place and the rest of the data stays internally consistent.

Run from the repo root:  python scripts/generate_sample_catalog.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from storefront_readiness.pricing import format_price  # noqa: E402

# Seeded issues the readiness review is expected to catch. Tests assert on them.
SEEDED_ISSUES = [
    "CA   fr-CA descriptions missing for four apps (translation completeness below gate)",
    "DE   de-DE title for Ledger Fitness exceeds the 30 character tile limit",
    "DE   imprint link missing (storefront.yaml, not this script)",
    "JP   Stillwater price shown with decimals ('¥600.00') in a zero-decimal currency",
    "SA   ar-SA listings missing for three apps; Vintner's Table conflicts with a content rule",
    "KR   Pixel Forge Arena has no rating in the KR scheme",
    "TR   Orbit Weather tr-TR description is a copy of the source string",
    "BR   Cardhouse Poker needs content review (warning only)",
    "FR   Aurora Cinema fr-FR description exceeds the soft limit (warning only)",
    "IN   hi-IN screenshot alt text missing for two apps (warning, above gate)",
    "NL   Pixel Forge Arena conflicts with a content rule",
]

LOCALES = [
    "en-US", "fr-CA", "es-MX", "pt-BR", "fr-FR", "de-DE", "es-ES", "it-IT",
    "nl-NL", "tr-TR", "ar-SA", "hi-IN", "ja-JP", "ko-KR",
]  # fmt: skip
# English variants (en-CA, en-GB, en-IN, en-AU) fall back to en-US in the market packs.

DESCRIPTIONS: dict[str, dict[str, str]] = {
    "video": {
        "en": "Stream new films and classic series in 4K, with watchlists synced across your devices.",
        "fr": "Regardez de nouveaux films et des séries cultes en 4K, avec des listes synchronisées sur tous vos appareils.",
        "es": "Mira estrenos y series clásicas en 4K, con listas sincronizadas en todos tus dispositivos.",
        "pt": "Assista a lançamentos e séries clássicas em 4K, com listas sincronizadas em todos os seus aparelhos.",
        "de": "Neue Filme und Kultserien in 4K streamen, mit Merklisten auf all deinen Geräten.",
        "it": "Guarda nuovi film e serie classiche in 4K, con liste sincronizzate su tutti i tuoi dispositivi.",
        "nl": "Stream nieuwe films en klassieke series in 4K, met kijklijsten op al je apparaten.",
        "tr": "Yeni filmleri ve klasik dizileri 4K kalitesinde izleyin, listeleriniz tüm cihazlarınızda senkronize olsun.",
        "ar": "شاهد أحدث الأفلام والمسلسلات الكلاسيكية بدقة 4K مع قوائم مشاهدة متزامنة على جميع أجهزتك.",
        "hi": "नई फ़िल्में और क्लासिक सीरीज़ 4K में देखें, सभी डिवाइस पर सिंक की गई वॉचलिस्ट के साथ।",
        "ja": "新作映画や名作シリーズを4Kで。ウォッチリストはすべてのデバイスで同期されます。",
        "ko": "최신 영화와 명작 시리즈를 4K로 감상하고, 모든 기기에서 보관함을 동기화하세요.",
    },
    "kids": {
        "en": "Ad-free cartoons and learning games, with parental controls for every profile.",
        "fr": "Dessins animés sans publicité et jeux éducatifs, avec contrôle parental pour chaque profil.",
        "es": "Dibujos animados sin anuncios y juegos educativos, con control parental para cada perfil.",
        "pt": "Desenhos sem anúncios e jogos educativos, com controle dos pais para cada perfil.",
        "de": "Werbefreie Zeichentrickserien und Lernspiele, mit Jugendschutz für jedes Profil.",
        "it": "Cartoni senza pubblicità e giochi educativi, con controllo parentale per ogni profilo.",
        "nl": "Reclamevrije tekenfilms en leerzame spelletjes, met ouderlijk toezicht per profiel.",
        "tr": "Reklamsız çizgi filmler ve eğitici oyunlar, her profil için ebeveyn denetimiyle.",
        "ar": "رسوم متحركة خالية من الإعلانات وألعاب تعليمية مع رقابة أبوية لكل ملف شخصي.",
        "hi": "बिना विज्ञापन वाले कार्टून और सीखने वाले गेम, हर प्रोफ़ाइल के लिए पैरेंटल कंट्रोल के साथ।",
        "ja": "広告なしのアニメと学習ゲーム。プロフィールごとにペアレンタルコントロールを設定できます。",
        "ko": "광고 없는 만화와 학습 게임, 프로필별 자녀 보호 기능을 제공합니다.",
    },
    "fitness": {
        "en": "Guided workouts and wellness sessions you can follow from your living room.",
        "fr": "Séances d'entraînement et de bien-être guidées, à suivre depuis votre salon.",
        "es": "Entrenamientos guiados y sesiones de bienestar para seguir desde tu sala.",
        "pt": "Treinos guiados e sessões de bem-estar para fazer na sua sala.",
        "de": "Geführte Workouts und Entspannungseinheiten für dein Wohnzimmer.",
        "it": "Allenamenti guidati e sessioni di benessere da seguire in salotto.",
        "nl": "Begeleide workouts en ontspanningssessies voor in je woonkamer.",
        "tr": "Oturma odanızda takip edebileceğiniz rehberli antrenmanlar ve sağlıklı yaşam seansları.",
        "ar": "تمارين موجهة وجلسات عافية يمكنك متابعتها من غرفة المعيشة.",
        "hi": "गाइडेड वर्कआउट और वेलनेस सेशन, जिन्हें आप अपने लिविंग रूम से फ़ॉलो कर सकते हैं।",
        "ja": "リビングで続けられるガイド付きワークアウトとウェルネスセッション。",
        "ko": "거실에서 따라 할 수 있는 가이드 운동과 웰니스 세션.",
    },
    "music": {
        "en": "Sing along to thousands of tracks with on-screen lyrics and party mode.",
        "fr": "Chantez sur des milliers de titres avec paroles à l'écran et mode soirée.",
        "es": "Canta miles de canciones con letras en pantalla y modo fiesta.",
        "pt": "Cante milhares de músicas com letras na tela e modo festa.",
        "de": "Sing mit bei tausenden Songs, mit Songtexten auf dem Bildschirm und Partymodus.",
        "it": "Canta migliaia di brani con testi a schermo e modalità festa.",
        "nl": "Zing mee met duizenden nummers, met songteksten op het scherm en feestmodus.",
        "tr": "Ekrandaki şarkı sözleri ve parti moduyla binlerce şarkıya eşlik edin.",
        "ar": "غنِّ مع آلاف الأغاني مع كلمات على الشاشة ووضع الحفلات.",
        "hi": "स्क्रीन पर बोल और पार्टी मोड के साथ हज़ारों गानों पर गाएँ।",
        "ja": "画面に歌詞を表示して、数千曲を歌えます。パーティーモードも搭載。",
        "ko": "화면 가사와 파티 모드로 수천 곡을 함께 부르세요.",
    },
    "news": {
        "en": "Live headlines and local weather, updated every few minutes.",
        "fr": "Les titres en direct et la météo locale, mis à jour en continu.",
        "es": "Titulares en directo y el tiempo local, actualizados cada pocos minutos.",
        "pt": "Manchetes ao vivo e previsão do tempo local, atualizadas a cada poucos minutos.",
        "de": "Live-Schlagzeilen und lokales Wetter, alle paar Minuten aktualisiert.",
        "it": "Notizie in diretta e meteo locale, aggiornati ogni pochi minuti.",
        "nl": "Live nieuwskoppen en lokaal weer, elke paar minuten bijgewerkt.",
        "tr": "Birkaç dakikada bir güncellenen canlı manşetler ve yerel hava durumu.",
        "ar": "عناوين مباشرة وطقس محلي يتم تحديثها كل بضع دقائق.",
        "hi": "लाइव सुर्खियाँ और स्थानीय मौसम, हर कुछ मिनट में अपडेट।",
        "ja": "ライブのヘッドラインと地域の天気を数分ごとに更新。",
        "ko": "몇 분마다 업데이트되는 실시간 헤드라인과 지역 날씨.",
    },
    "games": {
        "en": "Quick multiplayer matches designed for the TV remote and gamepad.",
        "fr": "Des parties multijoueur rapides, conçues pour la télécommande et la manette.",
        "es": "Partidas multijugador rápidas, pensadas para el mando a distancia y el control.",
        "pt": "Partidas multijogador rápidas, feitas para o controle remoto e o gamepad.",
        "de": "Schnelle Mehrspielerrunden, gemacht für Fernbedienung und Gamepad.",
        "it": "Partite multigiocatore veloci, pensate per telecomando e gamepad.",
        "nl": "Snelle multiplayerpotjes, gemaakt voor afstandsbediening en gamepad.",
        "tr": "Kumanda ve oyun kolu için tasarlanmış hızlı çok oyunculu maçlar.",
        "ar": "مباريات جماعية سريعة مصممة لجهاز التحكم عن بعد ويد التحكم.",
        "hi": "टीवी रिमोट और गेमपैड के लिए बनाए गए तेज़ मल्टीप्लेयर मैच।",
        "ja": "テレビのリモコンとゲームパッド向けに作られた、手軽なマルチプレイ対戦。",
        "ko": "TV 리모컨과 게임패드에 맞춘 빠른 멀티플레이 대전.",
    },
    "lifestyle": {
        "en": "Step-by-step recipes and wine pairings for weeknight cooking.",
        "fr": "Recettes pas à pas et accords mets et vins pour les repas de la semaine.",
        "es": "Recetas paso a paso y maridajes de vino para las cenas entre semana.",
        "pt": "Receitas passo a passo e harmonizações de vinho para o dia a dia.",
        "de": "Rezepte Schritt für Schritt und passende Weine für den Feierabend.",
        "it": "Ricette passo passo e abbinamenti con il vino per le cene in settimana.",
        "nl": "Stap-voor-stap recepten en wijnsuggesties voor doordeweekse avonden.",
        "tr": "Hafta içi akşam yemekleri için adım adım tarifler ve şarap eşleştirmeleri.",
        "ar": "وصفات خطوة بخطوة واقتراحات للمائدة لوجبات أيام الأسبوع.",
        "hi": "हफ़्ते के खाने के लिए स्टेप-बाय-स्टेप रेसिपी और वाइन पेयरिंग।",
        "ja": "平日の夕食に役立つ手順付きレシピとワインの組み合わせ。",
        "ko": "평일 저녁을 위한 단계별 레시피와 와인 페어링.",
    },
    "utility": {
        "en": "Hour-by-hour forecasts, radar maps, and severe weather alerts.",
        "fr": "Prévisions heure par heure, cartes radar et alertes météo.",
        "es": "Pronóstico por horas, mapas de radar y alertas meteorológicas.",
        "pt": "Previsão hora a hora, mapas de radar e alertas de tempo severo.",
        "de": "Stündliche Vorhersagen, Regenradar und Unwetterwarnungen.",
        "it": "Previsioni ora per ora, mappe radar e allerte meteo.",
        "nl": "Verwachtingen per uur, buienradar en weeralarmen.",
        "tr": "Saatlik tahminler, radar haritaları ve şiddetli hava uyarıları.",
        "ar": "توقعات كل ساعة وخرائط رادار وتنبيهات الطقس القاسي.",
        "hi": "घंटे-दर-घंटे पूर्वानुमान, रडार मैप और गंभीर मौसम अलर्ट।",
        "ja": "1時間ごとの予報、雨雲レーダー、警報と注意報。",
        "ko": "시간별 예보, 레이더 지도, 기상 특보 알림.",
    },
}  # fmt: skip

SCREEN_ALT = {
    "en": ("{t} home screen", "{t} detail screen"),
    "fr": ("Écran d'accueil de {t}", "Écran de détail de {t}"),
    "es": ("Pantalla de inicio de {t}", "Pantalla de detalle de {t}"),
    "pt": ("Tela inicial do {t}", "Tela de detalhes do {t}"),
    "de": ("{t} Startbildschirm", "{t} Detailansicht"),
    "it": ("Schermata iniziale di {t}", "Schermata di dettaglio di {t}"),
    "nl": ("Startscherm van {t}", "Detailscherm van {t}"),
    "tr": ("{t} ana ekranı", "{t} ayrıntı ekranı"),
    "ar": ("الشاشة الرئيسية لتطبيق {t}", "شاشة التفاصيل لتطبيق {t}"),
    "hi": ("{t} की होम स्क्रीन", "{t} की विवरण स्क्रीन"),
    "ja": ("{t}のホーム画面", "{t}の詳細画面"),
    "ko": ("{t} 홈 화면", "{t} 상세 화면"),
}

# maturity index -> value per rating scheme (schemes defined in data/rating_schemes.yaml)
RATING_LADDER = {
    "letter-4": ["ALL", "ALL", "10+", "TEEN", "MATURE"],
    "numeric-5": ["3", "7", "12", "16", "18"],
    "numeric-6": ["L", "10", "12", "14", "18"],
    "numeric-4k": ["ALL", "ALL", "12", "15", "19"],
    "numeric-au": ["G", "PG", "M", "MA15", "R18"],
}

# market -> (tier1, tier2) price amounts in the market currency
PRICE_TIERS = {
    "US": (4.99, 9.99), "CA": (6.49, 12.99), "MX": (89, 179), "BR": (24.90, 49.90),
    "GB": (4.49, 8.99), "FR": (4.99, 9.99), "DE": (4.99, 9.99), "ES": (4.99, 9.99),
    "IT": (4.99, 9.99), "NL": (4.99, 9.99), "TR": (149.99, 299.99), "SA": (18.99, 37.99),
    "IN": (399, 799), "JP": (600, 1200), "KR": (6500, 13000), "AU": (7.99, 14.99),
}  # fmt: skip

APPS = [
    # id, title, partner, category, maturity, tags, price tier (0 = free), excluded markets
    ("aurora-cinema", "Aurora Cinema", "Aurora Pictures Ltd.", "video", 3, [], 2, []),
    ("tidepool-kids", "Tidepool Kids", "Tidepool Learning", "kids", 0, [], 0, []),
    ("ledger-fitness", "Ledger Fitness", "Ledger Health Co.", "fitness", 0, [], 1, []),
    ("lantern-karaoke", "Lantern Karaoke", "Lantern Media", "music", 1,
     ["user_generated_content"], 0, []),
    ("meridian-news", "Meridian News", "Meridian Broadcast Group", "news", 1, [], 0, []),
    ("cardhouse-poker", "Cardhouse Poker", "Cardhouse Games", "games", 4,
     ["simulated_gambling"], 0, ["KR", "TR", "SA"]),
    ("vintners-table", "Vintner's Table", "Copperpot Studios", "lifestyle", 4, ["alcohol"], 0, []),
    ("pixel-forge-arena", "Pixel Forge Arena", "Pixel Forge Interactive", "games", 2,
     ["loot_boxes"], 1, []),
    ("stillwater", "Stillwater Meditation", "Stillwater Wellness", "fitness", 0, [], 1, []),
    ("orbit-weather", "Orbit Weather", "Orbit Data Labs", "utility", 0, [], 0, []),
]  # fmt: skip


def lang(locale: str) -> str:
    return locale.split("-")[0]


def listing(title: str, category: str, locale: str) -> dict:
    lg = lang(locale)
    alts = SCREEN_ALT[lg]
    return {
        "title": title,
        "description": DESCRIPTIONS[category][lg],
        "screenshots": [
            {"file": "home.png", "alt": alts[0].format(t=title)},
            {"file": "detail.png", "alt": alts[1].format(t=title)},
        ],
    }


def main() -> None:
    apps = []
    for app_id, title, partner, category, maturity, tags, tier, excluded in APPS:
        listings = {loc: listing(title, category, loc) for loc in LOCALES}
        ratings = {scheme: ladder[maturity] for scheme, ladder in RATING_LADDER.items()}
        app = {
            "id": app_id,
            "partner": partner,
            "category": category,
            "content_tags": tags,
            "exclude_markets": excluded,
            "ratings": ratings,
            "pricing": "free"
            if tier == 0
            else {m: {"amount": tiers[tier - 1]} for m, tiers in PRICE_TIERS.items()},
            "listings": listings,
        }
        apps.append(app)

    # Display strings come from the reference formatter, as a partner portal
    # would produce them, so that only the seeded defects below are wrong.
    packs = {
        p.stem.upper(): yaml.safe_load(p.read_text())["pricing"]
        for p in (ROOT / "data" / "markets").glob("*.yaml")
    }
    for app in apps:
        if app["pricing"] == "free":
            continue
        for market, price in app["pricing"].items():
            fmt = packs[market]
            price["currency"] = fmt["currency"]
            price["display"] = format_price(price["amount"], fmt)

    by_id = {a["id"]: a for a in apps}

    # ---- seeded issues -----------------------------------------------------
    for app_id in ("tidepool-kids", "meridian-news", "lantern-karaoke", "orbit-weather"):
        del by_id[app_id]["listings"]["fr-CA"]["description"]
    by_id["ledger-fitness"]["listings"]["de-DE"]["title"] = (
        "Ledger Fitness: Ganzkörpertraining für Zuhause"
    )
    for app_id in ("lantern-karaoke", "pixel-forge-arena", "orbit-weather"):
        del by_id[app_id]["listings"]["ar-SA"]
    del by_id["pixel-forge-arena"]["ratings"]["numeric-4k"]
    by_id["orbit-weather"]["listings"]["tr-TR"]["description"] = DESCRIPTIONS["utility"]["en"]
    by_id["aurora-cinema"]["listings"]["fr-FR"]["description"] += (
        " Profils illimités, téléchargements pour vos déplacements, sous-titres et audiodescription"
        " dans plus de vingt langues, contrôle parental avancé, recommandations personnalisées"
        " selon vos goûts et reprise de lecture instantanée d'un écran à l'autre, à la maison"
        " comme en vacances."
    )
    for app_id in ("meridian-news", "tidepool-kids"):
        by_id[app_id]["listings"]["hi-IN"]["screenshots"][1]["alt"] = ""
    # JP display string override: the price formatter at the partner portal
    # rendered two decimals for a zero-decimal currency.
    by_id["stillwater"]["pricing"]["JP"]["display"] = "¥600.00"

    out = {
        "_comment": "Synthetic sample data. All apps, partners, and strings are fictional. "
        "Generated by scripts/generate_sample_catalog.py; edit the script, not this file.",
        "apps": apps,
    }
    path = ROOT / "data" / "catalog.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=100))
    print(f"wrote {path.relative_to(ROOT)} with {len(apps)} apps")


if __name__ == "__main__":
    main()
