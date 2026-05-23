import json, os, hashlib, time
from io import BytesIO

try:
    from android import api_version
    _ON_ANDROID = True
except ImportError:
    _ON_ANDROID = False

from PIL import Image
import piexif

from bulkresizer.constants import EXTS_JPEG, EXTS_IMAGE, QUALITY_LEVELS, RES_LEVELS

def _load_exif(path):
    blank = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
    try:
        img = Image.open(path)
        raw = img.info.get("exif")
        if raw:
            return piexif.load(raw)
    except Exception:
        pass
    return blank

def read_meta(path):
    meta = {"exif_dict": None, "date_orig": None,
            "date_mod": None, "compressed": None}
    try:
        exif = _load_exif(path)
        meta["exif_dict"] = exif
        meta["date_orig"] = (
            exif.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal) or
            exif.get("0th",  {}).get(piexif.ImageIFD.DateTime)
        )
        meta["date_mod"] = exif.get("0th", {}).get(piexif.ImageIFD.DateTime)
        raw_uc = exif.get("Exif", {}).get(piexif.ExifIFD.UserComment)
        if raw_uc and len(raw_uc) > 8:
            try:
                txt = raw_uc[8:].decode("utf-8", errors="ignore").strip("\x00").strip()
                meta["compressed"] = json.loads(txt).get("compressed")
            except Exception:
                pass
    except Exception:
        pass
    return meta

def build_exif(exif_dict, date_orig, date_mod, compressed_val):
    try:
        if exif_dict is None:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
        if date_orig:
            exif_dict.setdefault("Exif", {})[piexif.ExifIFD.DateTimeOriginal] = date_orig
            exif_dict.setdefault("0th",  {})[piexif.ImageIFD.DateTime]        = date_orig
        if date_mod:
            exif_dict.setdefault("0th",  {})[piexif.ImageIFD.DateTime]        = date_mod
        if compressed_val is not None:
            payload = json.dumps({"compressed": compressed_val}, separators=(",", ":"))
            exif_dict.setdefault("Exif", {})[piexif.ExifIFD.UserComment] = (
                b"ASCII\x00\x00\x00" + payload.encode("utf-8")
            )
        else:
            exif_dict.get("Exif", {}).pop(piexif.ExifIFD.UserComment, None)
        return piexif.dump(exif_dict)
    except Exception:
        return None

def collect_images(folder, res_key="high", quality_key=None, on_found=None):
    max_width = RES_LEVELS.get(res_key, 2000)
    comp_pct  = QUALITY_LEVELS.get(quality_key)  # 15, 30, 45 or None (OFF)
    result = []
    for root, _, files in os.walk(folder):
        for fname in sorted(files):
            if os.path.splitext(fname)[1] not in EXTS_JPEG:
                continue
            fpath = os.path.join(root, fname)
            try:
                with Image.open(fpath) as img:
                    w, h = img.size
                meta    = read_meta(fpath)
                size_ko = os.path.getsize(fpath) // 1024
                prev_pct = meta.get("compressed")
                needs_resize = w > max_width
                skip_reason = None
                if not needs_resize:
                    if comp_pct is None:
                        skip_reason = "no_resize_no_comp"
                    elif prev_pct is not None and comp_pct <= prev_pct:
                        skip_reason = "already_opt"
                info = {"path": fpath, "name": fname,
                        "width": w, "height": h,
                        "size_ko": size_ko, "meta": meta,
                        "prev_pct": prev_pct,
                        "needs_resize": needs_resize,
                        "skip_reason": skip_reason}
                result.append(info)
                if on_found:
                    on_found(info)
            except Exception:
                pass
    return result

def process_image(info, res_key="high", quality_key=None):
    path        = info["path"]
    size_before = info["size_ko"]
    prev_pct    = info.get("prev_pct")
    max_width   = RES_LEVELS.get(res_key, 2000)
    comp_pct    = QUALITY_LEVELS.get(quality_key)  # 15, 30, 45 or None
    try:
        meta   = info["meta"]
        orig_w = info["width"]
        orig_h = info["height"]
        needs_resize = orig_w > max_width
        new_w  = max_width if needs_resize else orig_w
        new_h  = int(orig_h * new_w / orig_w)

        do_compress = comp_pct is not None and not (
            prev_pct is not None and comp_pct <= prev_pct
        )

        if not needs_resize and not do_compress:
            return {"ok": True, "new_w": new_w, "new_h": new_h,
                    "size_before_ko": size_before, "size_after_ko": size_before,
                    "skipped": True}

        with Image.open(path) as img:
            if needs_resize:
                resized = img.resize((new_w, new_h), Image.LANCZOS)
            else:
                resized = img
            if resized.mode in ("RGBA", "P", "LA"):
                resized = resized.convert("RGB")

            store_pct = comp_pct if do_compress else None
            exif_bytes = build_exif(meta["exif_dict"], meta["date_orig"],
                                    meta["date_mod"], store_pct)
            kwargs = {"optimize": True, "subsampling": 0}
            if exif_bytes:
                kwargs["exif"] = exif_bytes
            if do_compress:
                kwargs["quality"] = max(55, 100 - comp_pct)
            resized.save(path, "JPEG", **kwargs)

        size_after = os.path.getsize(path) // 1024
        return {"ok": True, "new_w": new_w, "new_h": new_h,
                "size_before_ko": size_before, "size_after_ko": size_after,
                "prev_pct": prev_pct, "quality_kept": not do_compress}
    except Exception as e:
        return {"ok": False, "new_w": 0, "new_h": 0,
                "size_before_ko": size_before, "size_after_ko": size_before,
                "error": str(e)}

def preview_image(filepath, max_width, quality):
    try:
        with Image.open(filepath) as img:
            orig_w, orig_h = img.size
            new_w = max_width
            new_h = int(orig_h * max_width / orig_w)
            resized = img.resize((new_w, new_h), Image.LANCZOS)
            if resized.mode in ("RGBA", "P", "LA"):
                resized = resized.convert("RGB")
            buf = BytesIO()
            resized.save(buf, "JPEG", quality=quality or 92, optimize=True)
            size_after = buf.tell() // 1024
            buf.seek(0)
            return resized, size_after
    except Exception:
        return None, 0

def format_bytes(ko):
    if ko >= 1024 * 1024:
        return f"{ko / (1024 * 1024):.1f} Go"
    if ko >= 1024:
        return f"{ko / 1024:.2f} Mo"
    return f"{ko} Ko"

def scan_folders(root, on_progress=None):
    folders = {}
    total = 0
    for root_dir, dirs, files in os.walk(root):
        img_count = 0
        img_size = 0
        for fname in files:
            ext = os.path.splitext(fname)[1]
            if ext not in EXTS_IMAGE:
                continue
            try:
                sz = os.path.getsize(os.path.join(root_dir, fname))
                img_count += 1
                img_size += sz
                total += 1
            except Exception:
                pass
        if img_count > 0:
            folders[root_dir] = (img_count, img_size // 1024)
        if on_progress and total % 20 == 0:
            on_progress(total)
    sorted_folders = sorted(folders.items(), key=lambda x: -x[1][1])
    return sorted_folders

_LICENSE_DIR = None

def _get_data_dir():
    global _LICENSE_DIR
    if _LICENSE_DIR:
        return _LICENSE_DIR
    for base in (
        os.environ.get("EXTERNAL_STORAGE"),
        os.path.expanduser("~"),
        "/sdcard",
        "/storage/emulated/0",
    ):
        if base and os.path.isdir(base):
            d = os.path.join(base, ".compresseurauto")
            try:
                os.makedirs(d, exist_ok=True)
                _LICENSE_DIR = d
                return d
            except Exception:
                pass
    return None

def _license_path():
    d = _get_data_dir()
    if not d:
        return None
    return os.path.join(d, "license.json")

def _device_id():
    try:
        import uuid
        return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:12]
    except Exception:
        return "unknown"

def read_license():
    path = _license_path()
    if not path or not os.path.isfile(path):
        return {"device_id": _device_id()}
    try:
        with open(path) as f:
            data = json.load(f)
        if data.get("device_id") != _device_id():
            data["device_id"] = _device_id()
        return data
    except Exception:
        return {"device_id": _device_id()}

def write_license(data):
    path = _license_path()
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass
