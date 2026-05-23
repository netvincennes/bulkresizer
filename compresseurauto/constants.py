import locale, os

BG_DARK   = (0.07, 0.09, 0.13, 1)
BG_CARD   = (0.12, 0.15, 0.21, 1)
BG_THUMB  = (0.10, 0.13, 0.19, 1)
BG_HEADER = (0.04, 0.06, 0.11, 1)
ACCENT    = (0.18, 0.62, 0.94, 1)
ACCENT2   = (0.10, 0.44, 0.74, 1)
SUCCESS   = (0.18, 0.80, 0.50, 1)
WARNING   = (0.98, 0.72, 0.15, 1)
DANGER    = (0.88, 0.25, 0.25, 1)
DONATION  = (0.95, 0.55, 0.10, 1)
TEXT_PRI  = (0.92, 0.94, 0.96, 1)
TEXT_SEC  = (0.55, 0.62, 0.70, 1)
TEXT_DIM  = (0.30, 0.36, 0.44, 1)

EXTS_JPEG   = {".jpg", ".jpeg", ".JPG", ".JPEG"}
EXTS_IMAGE  = {".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG", ".webp", ".WEBP"}
MAX_THUMBS  = 30
CONTACT_EMAIL = "info@netvincennes.fr"
ICON_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "compresseurauto.png")

# ─── Qualité (compression %) ──────────────────────────────────────────────
QUALITY_LEVELS = {"high": 15, "medium": 30, "low": 45}  # compression %, OFF = None
QUALITY_KEYS   = ["high", "medium", "low", "off"]
# JPEG quality = 100 - compression_pct, plancher 55 % (low)

# ─── Résolution (largeur max en px) ───────────────────────────────────────
RES_LEVELS     = {"high": 2000, "medium": 1500, "low": 1000}
RES_KEYS       = ["low", "medium", "high"]

_TR = {
    "fr": {
        "app_title":      "Compresseur-Auto",
        "app_sub":        "Outil gratuit de réduction d'images",
        "folder":         "📁  Dossier source",
        "browse":         "Parcourir",
        "no_folder":      "(aucun dossier sélectionné)",
        "resolution":     "📐  Résolution",
        "res_high":       "Haute 2000",
        "res_medium":     "Moyenne 1500",
        "res_low":        "Basse 1000",
        "compression":    "🗜  Compression",
        "q_off":          "OFF",
        "q_high":         "Haute",
        "q_medium":       "Moyenne",
        "q_low":          "Basse",
        "q_high_sub":     "15 %",
        "q_medium_sub":   "30 %",
        "q_low_sub":      "45 %",
        "scan":           "🔍  Analyser",
        "start":          "▶  Lancer le traitement",
        "waiting":        "En attente…",
        "scanning":       "Analyse en cours…",
        "no_image":       "Aucune image à traiter.\nVérifiez les réglages ou le dossier.",
        "found":          "trouvée(s)",
        "to_process":     "À traiter :",
        "already_opt":    "Déjà optimisées :",
        "all_opt":        "Toutes déjà optimales",
        "nothing_to_do":  "Rien à faire",
        "already_opt_done": "déjà optimale",
        "no_resize_needed": "pas de redim.",
        "quality_kept":   "qualité d'origine conservée",
        "processing":     "Traitement",
        "done":           "Terminé",
        "treated":        "traitées",
        "saved_ko":       "Ko économisés",
        "preview":        "🖼  Aperçu",
        "first30":        "(30 premières)",
        "thumb_wait":     "Les vignettes apparaîtront ici après l'analyse.",
        "proc_lbl":       "traitement…",
        "err_lbl":        "erreur",
        "choose_folder":  "Choisir un dossier",
        "select":         "✔ Sélectionner",
        "cancel":         "Annuler",
        "report_title":   "Rapport de traitement",
        "report_sub":     "Compresseur-Auto  •  Rapport de traitement",
        "ok_images":      "✔  Images traitées",
        "errors":         "✖  Erreurs",
        "size_before":    "Taille avant",
        "size_after":     "Taille après",
        "space_saved":    "💾  Espace économisé",
        "storage":        "💿  Stockage de l'appareil",
        "total_disk":     "Capacité totale",
        "used_disk":      "Utilisé",
        "freed":          "Libéré maintenant",
        "available":      "Disponible",
        "no_disk":        "Impossible de lire l'espace disque.",
        "legend":         ["Utilisé", "Libéré", "Libre"],
        "close":          "Fermer le rapport",
        "preview_title":  "🔍  Aperçu des réglages",
        "preview_sub":    "3 premières images avec vos réglages appliqués",
        "preview_orig":   "Original",
        "preview_after":  "Après réglages",
        "preview_est":    "📊  Estimation espace économisé",
        "preview_est_val":"~{sav} économisés sur {n} fichiers",
        "preview_zoomin": "🔍  Zoom avant",
        "preview_zoomout":"🔍  Zoom arrière",
        "preview_prev":   "◀  Précédent",
        "preview_next":   "Suivant  ▶",
        "preview_of":     "{i} / {n}",
        "preview_launch": "▶  Lancer le traitement ({n} images)",
        "preview_back":   "← Retour",
        "perm_denied":    "Permission refusée",
        "perm_msg":       "L'accès au stockage est nécessaire\npour lire et modifier les images.",
        "lang_switch":    "🌐 EN",
        "loading":        "Chargement…",
        "spinner":        ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"],
        "privacy":        "🔒  Confidentialité : tout le traitement est effectué localement sur votre appareil. Aucune image ne quitte votre téléphone. Pas de cloud, pas de collecte de données.",
        "contact":        "📧  Contact : {email}",
        "donate":         "☕  Offrir un café",
        "donate_url":     "https://pay.sumup.com/b2c/QTEL5TPU",
        "about_btn":      "🏢  Espace Info Vincennes",
        "about_name":     "David J. CHEMLA",
        "about_org":      "Espace Informatique de Vincennes",
        "about_address":  "26, rue de l\u0027église, 94300 Vincennes",
        "about_email":    "info@netvincennes.fr",
        "about_web":      "netvincennes.fr",
        "about_web_url":  "https://netvincennes.fr",
        "sg_ad_title":    "🔒  SecGuardian Mobile",
        "sg_ad_desc":     "Protection antivirus, VPN suisse, sauvegarde cloud,\ncompression vidéo et bien plus encore...",
        "sg_ad_link":     "https://secguardian.fr/mobile",
        "sg_desktop_title": "💻  SecGuardian Desktop",
        "sg_desktop_desc": "Sécurité, VPN sans logs (Suisse), DNS, pare-feu,\nsauvegarde Suisse, autostart, phone sync, cleaner, updates",
        "sg_desktop_link": "https://secguardian.fr",
    },
    "en": {
        "app_title":      "Compresseur-Auto",
        "app_sub":        "Free image reduction tool",
        "folder":         "📁  Source folder",
        "browse":         "Browse",
        "no_folder":      "(no folder selected)",
        "resolution":     "📐  Resolution",
        "res_high":       "High 2000",
        "res_medium":     "Medium 1500",
        "res_low":        "Low 1000",
        "compression":    "🗜  Compression",
        "q_off":          "OFF",
        "q_high":         "High",
        "q_medium":       "Medium",
        "q_low":          "Low",
        "q_high_sub":     "15 %",
        "q_medium_sub":   "30 %",
        "q_low_sub":      "45 %",
        "scan":           "🔍  Scan",
        "start":          "▶  Start processing",
        "waiting":        "Waiting…",
        "scanning":       "Scanning…",
        "no_image":       "No images to process.\nCheck settings or folder.",
        "found":          "found",
        "to_process":     "To process:",
        "already_opt":    "Already optimized:",
        "all_opt":        "All already optimal",
        "nothing_to_do":  "Nothing to do",
        "already_opt_done": "already optimal",
        "no_resize_needed": "no resize needed",
        "quality_kept":   "original quality preserved",
        "processing":     "Processing",
        "done":           "Done",
        "treated":        "processed",
        "saved_ko":       "Ko saved",
        "preview":        "🖼  Preview",
        "first30":        "(first 30)",
        "thumb_wait":     "Thumbnails will appear here after scanning.",
        "proc_lbl":       "processing…",
        "err_lbl":        "error",
        "choose_folder":  "Choose a folder",
        "select":         "✔ Select",
        "cancel":         "Cancel",
        "report_title":   "Processing Report",
        "report_sub":     "Compresseur-Auto  •  Processing Report",
        "ok_images":      "✔  Images processed",
        "errors":         "✖  Errors",
        "size_before":    "Size before",
        "size_after":     "Size after",
        "space_saved":    "💾  Space saved",
        "storage":        "💿  Device storage",
        "total_disk":     "Total capacity",
        "used_disk":      "Used",
        "freed":          "Freed now",
        "available":      "Available",
        "no_disk":        "Unable to read disk space.",
        "legend":         ["Used", "Freed", "Free"],
        "close":          "Close report",
        "preview_title":  "🔍  Settings preview",
        "preview_sub":    "First 3 images with your settings applied",
        "preview_orig":   "Original",
        "preview_after":  "After settings",
        "preview_est":    "📊  Estimated space savings",
        "preview_est_val":"~{sav} saved on {n} files",
        "preview_zoomin": "🔍  Zoom in",
        "preview_zoomout":"🔍  Zoom out",
        "preview_prev":   "◀  Previous",
        "preview_next":   "Next  ▶",
        "preview_of":     "{i} / {n}",
        "preview_launch": "▶  Process all ({n} images)",
        "preview_back":   "← Back",
        "perm_denied":    "Permission denied",
        "perm_msg":       "Storage access is required\nto read and modify images.",
        "lang_switch":    "🌐 FR",
        "loading":        "Loading…",
        "spinner":        ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"],
        "privacy":        "🔒  Privacy: all processing is done locally on your device. No image ever leaves your phone. No cloud, no data collection.",
        "contact":        "📧  Contact: {email}",
        "donate":         "☕  Buy me a coffee",
        "donate_url":     "https://pay.sumup.com/b2c/QTEL5TPU",
        "about_btn":      "🏢  Espace Info Vincennes",
        "about_name":     "David J. CHEMLA",
        "about_org":      "Espace Informatique de Vincennes",
        "about_address":  "26, rue de l\u0027église, 94300 Vincennes",
        "about_email":    "info@netvincennes.fr",
        "about_web":      "netvincennes.fr",
        "about_web_url":  "https://netvincennes.fr",
        "sg_ad_title":    "🔒  SecGuardian Mobile",
        "sg_ad_desc":     "Antivirus, Swiss VPN, cloud backup,\nvideo compression and much more...",
        "sg_ad_link":     "https://secguardian.fr/mobile",
        "sg_desktop_title": "💻  SecGuardian Desktop",
        "sg_desktop_desc": "Security, no-log VPN (Switzerland), DNS, firewall,\nSwiss backup, autostart, phone sync, cleaner, updates",
        "sg_desktop_link": "https://secguardian.fr",
    },
}

def _detect_lang():
    for var in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(var, "")
        if val.startswith("fr"):
            return "fr"
        if val.startswith("en"):
            return "en"
    try:
        lang = locale.getdefaultlocale()[0] or ""
        if lang.startswith("fr"):
            return "fr"
    except Exception:
        pass
    return "en"

LANG = _detect_lang()

def T(key):
    return _TR.get(LANG, _TR["en"]).get(key, _TR["en"].get(key, key))
