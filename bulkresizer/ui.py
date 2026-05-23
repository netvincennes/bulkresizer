import os, json, threading, time, webbrowser, shutil, tempfile

from kivy.uix.boxlayout   import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview  import ScrollView
from kivy.uix.label       import Label
from kivy.uix.button      import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup       import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.image       import AsyncImage
from kivy.uix.relativelayout import RelativeLayout
from kivy.clock           import Clock
from kivy.metrics         import dp, sp
from kivy.graphics        import Color, RoundedRectangle, Rectangle

from bulkresizer.constants import (
    BG_DARK, BG_CARD, BG_THUMB, BG_HEADER,
    ACCENT, ACCENT2, SUCCESS, WARNING, DANGER, DONATION,
    TEXT_PRI, TEXT_SEC, TEXT_DIM,
    MAX_THUMBS, CONTACT_EMAIL, ICON_PATH,
    QUALITY_LEVELS, QUALITY_KEYS, RES_LEVELS, RES_KEYS,
    T,
)
import bulkresizer.constants as _c
from bulkresizer.core import (
    collect_images, process_image, preview_image,
    scan_folders, format_bytes,
)

# ─── Widgets de base ─────────────────────────────────────────────────────────

class CardBox(BoxLayout):
    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding",     [dp(12), dp(10), dp(12), dp(10)])
        kwargs.setdefault("spacing",     dp(6))
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*BG_CARD)
            self._r = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=lambda *_: setattr(self._r, "pos",  self.pos),
                  size=lambda *_: setattr(self._r, "size", self.size))

class H2(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("color",       TEXT_PRI)
        kwargs.setdefault("font_size",   sp(14))
        kwargs.setdefault("bold",        True)
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height",      dp(26))
        kwargs.setdefault("halign",      "left")
        kwargs.setdefault("valign",      "middle")
        super().__init__(**kwargs)
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))

class Sub(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("color",       TEXT_SEC)
        kwargs.setdefault("font_size",   sp(11))
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height",      dp(18))
        kwargs.setdefault("halign",      "left")
        kwargs.setdefault("valign",      "middle")
        super().__init__(**kwargs)
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))

class Btn(Button):
    def __init__(self, color=ACCENT, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_color",  color)
        kwargs.setdefault("color",             (1, 1, 1, 1))
        kwargs.setdefault("font_size",         sp(13))
        kwargs.setdefault("bold",              True)
        kwargs.setdefault("size_hint_y",       None)
        kwargs.setdefault("height",            dp(44))
        super().__init__(**kwargs)

# ─── Vignette d'image ────────────────────────────────────────────────────────

CARD_W = dp(96)
CARD_H = dp(152)

class ThumbCard(BoxLayout):
    def __init__(self, info, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint=(None, None), size=(CARD_W, CARD_H),
            spacing=dp(2), padding=[dp(4), dp(4)], **kwargs
        )
        self._info = info
        with self.canvas.before:
            Color(*BG_THUMB)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])
        self.bind(pos=lambda *_: setattr(self._bg, "pos",  self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))

        self.img = AsyncImage(
            source=info["path"],
            size_hint=(1, None), height=dp(80),
            nocache=True,
        )
        self.add_widget(self.img)

        name  = info["name"]
        short = (name[:11] + "\u2026") if len(name) > 12 else name
        for txt, col, fs, h in [
            (short,                          TEXT_PRI, sp(9),  dp(16)),
            (f"{info['width']}\u00d7{info['height']}", TEXT_DIM, sp(8), dp(13)),
            (f"{info['size_ko']} Ko",         TEXT_DIM, sp(8),  dp(13)),
        ]:
            lbl = Label(text=txt, color=col, font_size=fs,
                        size_hint_y=None, height=h,
                        halign="center", valign="middle")
            lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
            self.add_widget(lbl)

        self._lbl_status = Label(
            text="", color=TEXT_DIM, font_size=sp(9),
            size_hint_y=None, height=dp(14), halign="center", valign="middle")
        self._lbl_status.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        self.add_widget(self._lbl_status)

        skip = info.get("skip_reason")
        if skip == "already_opt":
            self._lbl_status.text  = f"\u2705 {T('already_opt_done')}"
            self._lbl_status.color = TEXT_DIM
        elif skip == "no_resize_no_comp":
            self._lbl_status.text  = T("no_resize_needed")
            self._lbl_status.color = TEXT_DIM

    def set_processing(self):
        self._lbl_status.text  = f"\u23f3 {T('proc_lbl')}"
        self._lbl_status.color = WARNING

    def set_done(self, ok, size_after_ko=0, error_msg=""):
        saved = self._info["size_ko"] - size_after_ko
        if ok:
            self._lbl_status.text  = f"\u2714 -{saved}Ko"
            self._lbl_status.color = SUCCESS
        else:
            short = error_msg[:18] + "\u2026" if len(error_msg) > 20 else error_msg
            self._lbl_status.text  = f"\u2716 {short}"
            self._lbl_status.color = DANGER

# ─── Popup sélecteur dossier ──────────────────────────────────────────────────

class FolderPopup(Popup):
    def __init__(self, on_select, **kwargs):
        super().__init__(
            title=T("choose_folder"),
            size_hint=(0.95, 0.88),
            background_color=BG_DARK,
            title_color=TEXT_PRI,
            separator_color=ACCENT, **kwargs
        )
        self._cb = on_select
        lay = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        self.fc = FileChooserListView(path=self._start(),
                                      dirselect=True, show_hidden=False)
        lay.add_widget(self.fc)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        ok     = Btn(text=T("select"), color=ACCENT)
        cancel = Btn(text=T("cancel"), color=(0.28, 0.30, 0.35, 1))
        ok.bind(on_press=self._ok)
        cancel.bind(on_press=self.dismiss)
        row.add_widget(ok); row.add_widget(cancel)
        lay.add_widget(row)
        self.content = lay

    @staticmethod
    def _start():
        cands = []
        ext = os.environ.get("EXTERNAL_STORAGE")
        if ext:
            cands += [os.path.join(ext, "DCIM"), ext]
        cands.append(os.path.expanduser("~"))
        cands += ["/sdcard/DCIM", "/sdcard",
                  "/storage/emulated/0/DCIM", "/storage/emulated/0", "/"]
        for p in cands:
            if os.path.isdir(p):
                return p
        return "/"

    def _ok(self, *_):
        sel  = self.fc.selection
        path = sel[0] if sel else self.fc.path
        if os.path.isdir(path):
            self._cb(path); self.dismiss()

# ─── Rapport plein écran ──────────────────────────────────────────────────────

def _disk_info(folder):
    try:
        usage = shutil.disk_usage(folder)
        return usage.total // 1024, usage.used // 1024, usage.free // 1024
    except Exception:
        for p in ("/sdcard", "/storage/emulated/0", os.path.expanduser("~")):
            try:
                u = shutil.disk_usage(p)
                return u.total // 1024, u.used // 1024, u.free // 1024
            except Exception:
                pass
    return 0, 0, 0

def _rgba_hex(rgba):
    r, g, b = int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255)
    return f"{r:02x}{g:02x}{b:02x}"

class ReportScreen(FloatLayout):
    def __init__(self, n_ok, n_err, before_ko, after_ko, folder, on_close,
                 skipped=0, **kwargs):
        super().__init__(**kwargs)

        saved_ko  = max(0, before_ko - after_ko)
        pct_saved = (saved_ko / before_ko * 100) if before_ko > 0 else 0
        total_disk, used_disk, free_disk = _disk_info(folder or "/sdcard")

        def fmt(ko):
            if ko >= 1024 * 1024:
                return f"{ko/1024/1024:.1f} Go"
            if ko >= 1024:
                return f"{ko/1024:.2f} Mo"
            return f"{ko} Ko"

        with self.canvas.before:
            Color(*BG_DARK)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos",  self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))

        btn_x = Button(
            text="\u2715", size_hint=(None, None), size=(dp(44), dp(44)),
            pos_hint={"right": 1.0, "top": 1.0},
            background_normal="", background_color=(0.20, 0.24, 0.32, 1),
            color=TEXT_SEC, font_size=sp(18), bold=True,
        )
        btn_x.bind(on_press=lambda *_: on_close())
        self.add_widget(btn_x)

        sv = ScrollView(size_hint=(1, 1))
        inner = BoxLayout(
            orientation="vertical", size_hint_y=None,
            spacing=dp(12),
            padding=[dp(20), dp(56), dp(20), dp(30)],
        )
        inner.bind(minimum_height=inner.setter("height"))

        inner.add_widget(Label(
            text=f"[b]{T('report_title')}[/b]",
            markup=True, color=ACCENT, font_size=sp(22),
            size_hint_y=None, height=dp(36), halign="center",
        ))
        inner.add_widget(Label(
            text=T("report_sub"), color=TEXT_DIM, font_size=sp(11),
            size_hint_y=None, height=dp(20), halign="center",
        ))

        def stat_row(label, value, vcolor=TEXT_PRI):
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            lbl = Label(text=label, color=TEXT_SEC, font_size=sp(14),
                        halign="left", valign="middle", size_hint_x=0.60)
            lbl.bind(size=lambda *_: setattr(lbl, "text_size", lbl.size))
            val = Label(text=value, color=vcolor, font_size=sp(16),
                        bold=True, halign="right", valign="middle",
                        size_hint_x=0.40)
            val.bind(size=lambda *_: setattr(val, "text_size", val.size))
            row.add_widget(lbl); row.add_widget(val)
            return row

        def sep():
            s = Label(size_hint_y=None, height=dp(1))
            with s.canvas:
                Color(0.20, 0.25, 0.34, 1)
                _r = Rectangle(pos=s.pos, size=s.size)
            s.bind(pos=lambda w, *_: setattr(_r, "pos",  w.pos),
                   size=lambda w, *_: setattr(_r, "size", w.size))
            return s

        card_res = CardBox(padding=[dp(16), dp(12), dp(16), dp(12)], spacing=dp(2))
        card_res.add_widget(stat_row(T("ok_images"), str(n_ok), SUCCESS))
        if skipped:
            card_res.add_widget(stat_row(T("already_opt"), str(skipped), TEXT_DIM))
        if n_err:
            card_res.add_widget(stat_row(T("errors"), str(n_err), DANGER))
        card_res.add_widget(sep())
        card_res.add_widget(stat_row(T("size_before"), fmt(before_ko)))
        card_res.add_widget(stat_row(T("size_after"),  fmt(after_ko)))
        card_res.add_widget(sep())
        card_res.add_widget(stat_row(
            T("space_saved"),
            f"{fmt(saved_ko)}  ({pct_saved:.1f} %)",
            SUCCESS if saved_ko > 0 else WARNING,
        ))
        inner.add_widget(card_res)

        card_disk = CardBox(padding=[dp(16), dp(12), dp(16), dp(12)], spacing=dp(8))
        card_disk.add_widget(H2(text=T("storage")))

        if total_disk > 0:
            used_after_ko  = used_disk - saved_ko
            pct_used       = min(1.0, used_after_ko / total_disk)
            pct_saved_disk = min(1.0 - pct_used, saved_ko / total_disk)

            card_disk.add_widget(stat_row(T("total_disk"), fmt(total_disk)))
            card_disk.add_widget(stat_row(T("used_disk"),  fmt(used_after_ko), WARNING))
            card_disk.add_widget(stat_row(T("freed"),      fmt(saved_ko),      SUCCESS))
            card_disk.add_widget(stat_row(T("available"),  fmt(free_disk + saved_ko), ACCENT))
            card_disk.add_widget(sep())

            legend_labels = T("legend")
            legend = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(16))
            for dot_color, txt in [
                ((0.38, 0.44, 0.54, 1), legend_labels[0]),
                (SUCCESS,               legend_labels[1]),
                (ACCENT,                legend_labels[2]),
            ]:
                dot_lbl = Label(
                    text=f"[color={_rgba_hex(dot_color)}]\u25cf[/color]  {txt}",
                    markup=True, color=TEXT_DIM, font_size=sp(11),
                    size_hint_y=None, height=dp(18), halign="center",
                )
                legend.add_widget(dot_lbl)
            card_disk.add_widget(legend)

            bar = BoxLayout(size_hint_y=None, height=dp(26))
            with bar.canvas.before:
                Color(0.10, 0.13, 0.19, 1)
                _bbg = RoundedRectangle(pos=bar.pos, size=bar.size, radius=[dp(5)])
            bar.bind(pos=lambda w, *_: setattr(_bbg, "pos",  w.pos),
                     size=lambda w, *_: setattr(_bbg, "size", w.size))

            seg_used = Label(size_hint=(None, 1), width=dp(4))
            with seg_used.canvas.before:
                Color(0.35, 0.40, 0.50, 1)
                _ru = RoundedRectangle(pos=seg_used.pos, size=seg_used.size,
                                       radius=[dp(5), dp(0), dp(0), dp(5)])
            seg_used.bind(pos=lambda w, *_: setattr(_ru, "pos",  w.pos),
                          size=lambda w, *_: setattr(_ru, "size", w.size))

            seg_saved = Label(size_hint=(None, 1), width=dp(4))
            with seg_saved.canvas.before:
                Color(*SUCCESS)
                _rs = Rectangle(pos=seg_saved.pos, size=seg_saved.size)
            seg_saved.bind(pos=lambda w, *_: setattr(_rs, "pos",  w.pos),
                           size=lambda w, *_: setattr(_rs, "size", w.size))

            seg_free = Label(size_hint=(1, 1))
            with seg_free.canvas.before:
                Color(0.12, 0.30, 0.52, 1)
                _rf = RoundedRectangle(pos=seg_free.pos, size=seg_free.size,
                                       radius=[dp(0), dp(0), dp(5), dp(5)])
            seg_free.bind(pos=lambda w, *_: setattr(_rf, "pos",  w.pos),
                          size=lambda w, *_: setattr(_rf, "size", w.size))

            bar.add_widget(seg_used)
            bar.add_widget(seg_saved)
            bar.add_widget(seg_free)
            card_disk.add_widget(bar)

            def _size_bar(dt):
                total_w = bar.width
                seg_used.width  = max(dp(4), int(total_w * pct_used))
                seg_saved.width = max(dp(2), int(total_w * pct_saved_disk))
            Clock.schedule_once(_size_bar, 0.12)
        else:
            card_disk.add_widget(Sub(text=T("no_disk"), color=TEXT_DIM))

        inner.add_widget(card_disk)
        inner.add_widget(Label(size_hint_y=None, height=dp(8)))

        btn_close = Btn(text=T("close"), color=ACCENT2, height=dp(48))
        btn_close.bind(on_press=lambda *_: on_close())
        inner.add_widget(btn_close)

        sv.add_widget(inner)
        self.add_widget(sv)
        self.remove_widget(btn_x)
        self.add_widget(btn_x)

# ─── Écran prévisualisation ─────────────────────────────────────────────────

N_SAMPLE = 10

class PreviewScreen(FloatLayout):
    def __init__(self, images, res_key, quality_key, folder, on_launch, on_back, **kwargs):
        super().__init__(**kwargs)
        self._images = images
        self._on_launch = on_launch
        self._on_back = on_back
        self._idx = 0
        self._sample_data = []
        self._est_before = 0
        self._est_after = 0
        self._temp_dirs = []

        with self.canvas.before:
            Color(*BG_DARK)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos", self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))

        outer = BoxLayout(orientation="vertical", spacing=dp(4),
                          padding=[dp(0), dp(4), dp(0), dp(4)])

        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6),
                        padding=[dp(10), 0])
        top.add_widget(Label(
            text=f"[b]{T('preview_title')}[/b]",
            markup=True, color=ACCENT, font_size=sp(16),
            halign="left", valign="middle",
        ))
        top.add_widget(Label())
        btn_x = Button(
            text="\u2715", size_hint=(None, None), size=(dp(40), dp(36)),
            background_normal="", background_color=(0.20, 0.24, 0.32, 1),
            color=TEXT_SEC, font_size=sp(16), bold=True,
        )
        btn_x.bind(on_press=lambda *_: (self._cleanup(), on_back()))
        top.add_widget(btn_x)
        outer.add_widget(top)

        self._img_area = BoxLayout(orientation="vertical")
        outer.add_widget(self._img_area)

        bottom = BoxLayout(orientation="vertical", size_hint_y=None,
                           spacing=dp(2), padding=[dp(6), dp(4), dp(6), dp(8)])

        nav = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        self._btn_prev = Btn(text=T("preview_prev"), color=ACCENT2, height=dp(36))
        self._btn_prev.bind(on_press=self._prev)
        self._lbl_counter = Label(text="", color=TEXT_PRI, font_size=sp(13),
                                  bold=True, size_hint_x=0.3, halign="center")
        self._btn_next = Btn(text=T("preview_next"), color=ACCENT2, height=dp(36))
        self._btn_next.bind(on_press=self._next)
        nav.add_widget(self._btn_prev)
        nav.add_widget(self._lbl_counter)
        nav.add_widget(self._btn_next)
        bottom.add_widget(nav)

        zoom = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        self._btn_zoomin = Btn(text=T("preview_zoomin"), color=ACCENT2, height=dp(32))
        self._btn_zoomin.bind(on_press=self._zoom_in)
        self._lbl_zoom = Label(text="1\u00d7", color=TEXT_PRI, font_size=sp(12),
                               bold=True, size_hint_x=0.2, halign="center")
        self._btn_zoomout = Btn(text=T("preview_zoomout"), color=ACCENT2, height=dp(32))
        self._btn_zoomout.bind(on_press=self._zoom_out)
        zoom.add_widget(self._btn_zoomin)
        zoom.add_widget(self._lbl_zoom)
        zoom.add_widget(self._btn_zoomout)
        bottom.add_widget(zoom)

        bottom.add_widget(Label(size_hint_y=None, height=dp(2)))
        self._lbl_est = Label(
            text="", color=SUCCESS, font_size=sp(13), bold=True,
            size_hint_y=None, height=dp(24), halign="center",
        )
        bottom.add_widget(self._lbl_est)

        action_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_back = Btn(text=T("preview_back"), color=(0.28, 0.30, 0.35, 1), height=dp(42))
        btn_back.bind(on_press=lambda *_: (self._cleanup(), on_back()))
        self._btn_launch = Btn(text="", color=SUCCESS, height=dp(42))
        self._btn_launch.bind(on_press=lambda *_: (self._cleanup(), on_launch()))
        action_row.add_widget(btn_back)
        action_row.add_widget(self._btn_launch)
        bottom.add_widget(action_row)

        outer.add_widget(bottom)
        self.add_widget(outer)

        self._spinner_idx = 0
        self._spinner_chars = ["\u280b","\u2819","\u2839","\u2838","\u283c","\u2834","\u2826","\u2827","\u2807","\u280f"]
        self._spinner_lbl = Label(
            text=self._spinner_chars[0], color=TEXT_SEC, font_size=sp(36),
            halign="center", valign="center",
        )
        self._img_area.add_widget(self._spinner_lbl)
        self._spinner_ev = Clock.schedule_interval(self._spin, 0.08)
        Clock.schedule_once(lambda dt: self._compute_samples(res_key, quality_key), 0.1)

    def _spin(self, dt):
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_chars)
        self._spinner_lbl.text = self._spinner_chars[self._spinner_idx]

    def _compute_samples(self, res_key, quality_key):
        n = min(N_SAMPLE, len(self._images))
        samples = self._images[:n]
        ratio_sum = 0.0
        ratio_count = 0
        max_width = RES_LEVELS[res_key]
        if quality_key == "off":
            quality = None
        else:
            quality = max(55, 100 - QUALITY_LEVELS[quality_key])

        for info in samples:
            resized, size_after = preview_image(info["path"], max_width, quality)
            if resized:
                td = tempfile.mkdtemp()
                self._temp_dirs.append(td)
                tp = os.path.join(td, f"preview_{info['name']}")
                resized.save(tp, "JPEG", quality=92)
                self._sample_data.append((info, tp, resized, size_after))
                ratio_sum += size_after / info["size_ko"]
                ratio_count += 1

        self._spinner_ev.cancel()

        if not self._sample_data:
            self._img_area.clear_widgets()
            self._img_area.add_widget(Label(
                text=T("no_image"), color=WARNING, font_size=sp(16),
                halign="center", valign="center",
            ))
            self._btn_launch.text = T("preview_launch").format(n=len(self._images))
            return

        avg_ratio = ratio_sum / ratio_count
        self._est_before = sum(i["size_ko"] for i in self._images)
        self._est_after = int(sum(i["size_ko"] * avg_ratio for i in self._images))
        saved = max(0, self._est_before - self._est_after)
        pct = saved / self._est_before * 100 if self._est_before > 0 else 0

        def fmt(ko):
            if ko >= 1024 * 1024: return f"{ko/1024/1024:.1f} Go"
            if ko >= 1024: return f"{ko/1024:.2f} Mo"
            return f"{ko} Ko"
        self._lbl_est.text = f"{T('preview_est')}  {fmt(saved)}  ({pct:.1f}%)"
        self._btn_launch.text = T("preview_launch").format(n=len(self._images))
        self._idx = 0
        self._show_image()

    def _show_image(self):
        self._img_area.clear_widgets()
        n = len(self._sample_data)
        if n == 0:
            return
        info, thumb_path, resized, size_after = self._sample_data[self._idx]

        c = Label(text=T("preview_of").format(i=self._idx + 1, n=n),
                  color=TEXT_DIM, font_size=sp(11),
                  size_hint_y=None, height=dp(18), halign="center",
                  valign="middle")
        self._img_area.add_widget(c)

        info_lbl = Label(
            text=f"{info['name']}  \u2022  {resized.width}\u00d7{resized.height}  \u2022  ~{size_after} Ko",
            color=TEXT_SEC, font_size=sp(10),
            size_hint_y=None, height=dp(18), halign="center",
            valign="middle",
        )
        self._img_area.add_widget(info_lbl)

        sep = BoxLayout(size_hint_y=None, height=dp(1))
        with sep.canvas:
            Color(0.20, 0.25, 0.34, 1)
            self._sep_r = Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(pos=lambda w, *_: setattr(self._sep_r, "pos", w.pos),
                 size=lambda w, *_: setattr(self._sep_r, "size", w.size))
        self._img_area.add_widget(sep)

        self._zoom = 1.0
        img_sv = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=True)
        container = RelativeLayout(size_hint=(None, None))
        self._img_widget = AsyncImage(
            source=thumb_path,
            size_hint=(None, None),
        )
        container.bind(size=self._update_img_size)
        container.add_widget(self._img_widget)
        img_sv.add_widget(container)
        self._img_area.add_widget(img_sv)
        self._img_sv = img_sv
        Clock.schedule_once(lambda dt: self._update_img_size(), 0.1)

        self._btn_prev.disabled = self._idx <= 0
        self._btn_next.disabled = self._idx >= n - 1
        self._lbl_counter.text = T("preview_of").format(i=self._idx + 1, n=n)
        self._lbl_zoom.text = f"{self._zoom:.1f}\u00d7"

    def _update_img_size(self, *_):
        if not self._img_area.children:
            return
        img_sv = self._img_area.children[0]
        if not hasattr(img_sv, "children") or not img_sv.children:
            return
        container = img_sv.children[0]
        if not hasattr(container, "children") or not container.children:
            return
        base_w = img_sv.width
        base_h = img_sv.height
        if base_w <= 1 or base_h <= 1:
            return
        img_w = base_w * self._zoom
        img_h = base_h * self._zoom
        container.size = (img_w, img_h)
        self._img_widget.size = (img_w, img_h)
        self._img_widget.center = (img_w / 2, img_h / 2)

    def _prev(self, *_):
        if self._idx > 0:
            self._idx -= 1
            self._show_image()

    def _next(self, *_):
        if self._idx < len(self._sample_data) - 1:
            self._idx += 1
            self._show_image()

    def _zoom_in(self, *_):
        levels = [1.0, 1.5, 2.0, 3.0, 4.0]
        for lv in levels:
            if self._zoom < lv - 0.01:
                self._zoom = lv
                break
        else:
            self._zoom = levels[-1]
        self._update_img_size()
        self._lbl_zoom.text = f"{self._zoom:.1f}\u00d7"

    def _zoom_out(self, *_):
        levels = [4.0, 3.0, 2.0, 1.5, 1.0]
        for lv in levels:
            if self._zoom > lv + 0.01:
                self._zoom = lv
                break
        else:
            self._zoom = 1.0
        self._update_img_size()
        self._lbl_zoom.text = f"{self._zoom:.1f}\u00d7"

    def _cleanup(self):
        for td in self._temp_dirs:
            try:
                shutil.rmtree(td, ignore_errors=True)
            except Exception:
                pass

# ─── Popup À propos ────────────────────────────────────────────────────────────

class AboutPopup(FloatLayout):
    def __init__(self, on_dismiss, **kwargs):
        super().__init__(**kwargs)
        self._on_dismiss = on_dismiss
        with self.canvas.before:
            Color(0, 0, 0, 0.82)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos", self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))

        outer = BoxLayout(orientation="vertical", size_hint=(0.85, None),
                          pos_hint={"center_x": 0.5, "center_y": 0.5})
        outer.bind(minimum_height=outer.setter("height"))
        with outer.canvas.before:
            Color(*BG_CARD)
            self._cr = RoundedRectangle(pos=outer.pos, size=outer.size,
                                        radius=[dp(12)])
        outer.bind(pos=lambda *_: setattr(self._cr, "pos", outer.pos),
                   size=lambda *_: setattr(self._cr, "size", outer.size))

        inner = BoxLayout(orientation="vertical", size_hint_y=None,
                          spacing=dp(6), padding=[dp(16), dp(16), dp(16), dp(12)])
        inner.bind(minimum_height=inner.setter("height"))

        inner.add_widget(Label(
            text=f"[b]{T('about_name')}[/b]", markup=True,
            color=ACCENT, font_size=sp(18),
            size_hint_y=None, height=dp(28), halign="center",
        ))
        inner.add_widget(Label(
            text=T("about_org"), color=TEXT_SEC, font_size=sp(13),
            size_hint_y=None, height=dp(18), halign="center",
        ))
        inner.add_widget(Label(
            text=T("about_address"), color=TEXT_DIM, font_size=sp(11),
            size_hint_y=None, height=dp(16), halign="center",
        ))
        inner.add_widget(Label(size_hint_y=None, height=dp(4)))
        inner.add_widget(Label(
            text=T("about_email"), color=ACCENT2, font_size=sp(12),
            size_hint_y=None, height=dp(20), halign="center",
        ))
        inner.add_widget(Label(size_hint_y=None, height=dp(8)))

        btn_web = Btn(
            text="🌐  " + T("about_web"),
            color=ACCENT2, height=dp(40),
        )
        btn_web.bind(on_press=lambda *_: webbrowser.open(
            _c._TR.get(_c.LANG, _c._TR["en"]).get("about_web_url",
            _c._TR["en"]["about_web_url"])))
        inner.add_widget(btn_web)

        btn_donate = Btn(
            text=T("donate"),
            color=DONATION, height=dp(40),
        )
        btn_donate.bind(on_press=lambda *_: webbrowser.open(
            _c._TR.get(_c.LANG, _c._TR["en"]).get("donate_url",
            _c._TR["en"]["donate_url"])))
        inner.add_widget(btn_donate)

        inner.add_widget(Label(size_hint_y=None, height=dp(6)))

        btn_close = Btn(
            text="✕  Fermer" if _c.LANG == "fr" else "✕  Close",
            color=(0.30, 0.34, 0.40, 1), height=dp(40),
        )
        btn_close.bind(on_press=lambda *_: on_dismiss())
        inner.add_widget(btn_close)

        outer.add_widget(inner)
        self.add_widget(outer)

# ─── Écran principal ──────────────────────────────────────────────────────────

class MainScreen(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._folder      = ""
        self._images      = []
        self._cancelled   = False
        self._thumb_cards = {}
        self._res_key     = "high"
        self._quality_key = "high"

        with self.canvas.before:
            Color(*BG_DARK)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos",  self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))

        self._build()

    def _build(self):
        self.clear_widgets()
        self._thumb_cards = {}

        self._main = BoxLayout(orientation="vertical",
                               size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self._main.add_widget(self._make_header())

        scroll = ScrollView(size_hint=(1, 1))
        inner  = BoxLayout(orientation="vertical", size_hint_y=None,
                           spacing=dp(10), padding=[dp(10), dp(8), dp(10), dp(24)])
        inner.bind(minimum_height=inner.setter("height"))

        inner.add_widget(self._make_card_folder())
        inner.add_widget(self._make_card_resolution())
        inner.add_widget(self._make_card_quality())

        self.lbl_summary = Sub(text="", halign="center",
                                size_hint_y=None, height=dp(20))
        inner.add_widget(self.lbl_summary)
        inner.add_widget(self._make_btn_row())
        inner.add_widget(self._make_card_progress())
        inner.add_widget(self._make_card_thumbs())
        inner.add_widget(self._make_ad_section())

        scroll.add_widget(inner)
        self._main.add_widget(scroll)
        self.add_widget(self._main)
        self._update_summary()

    def _make_header(self):
        hdr = BoxLayout(orientation="vertical",
                        size_hint_y=None, height=dp(56),
                        padding=[dp(10), dp(6)])
        with hdr.canvas.before:
            Color(*BG_HEADER)
            r = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w, *_: setattr(r, "pos",  w.pos),
                 size=lambda w, *_: setattr(r, "size", w.size))

        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        if os.path.isfile(ICON_PATH):
            from kivy.uix.image import Image as KvImg
            row.add_widget(KvImg(
                source=ICON_PATH,
                size_hint=(None, None), size=(dp(34), dp(34)),
            ))

        title_col = BoxLayout(orientation="vertical", spacing=0, size_hint_x=0.45)
        title = Label(
            text=f"[b]{T('app_title')}[/b]", markup=True,
            color=ACCENT, font_size=sp(17),
            size_hint_y=None, height=dp(22), halign="left",
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        sub1 = Sub(text=T("app_sub"), color=TEXT_PRI,
                   size_hint_y=None, height=dp(18), font_size=sp(11))
        title_col.add_widget(title)
        title_col.add_widget(sub1)
        row.add_widget(title_col)

        row.add_widget(Label())

        btn_lang = Button(
            text=T("lang_switch"),
            size_hint=(None, None), size=(dp(56), dp(26)),
            background_normal="", background_color=ACCENT2,
            color=(1, 1, 1, 1), font_size=sp(10), bold=True,
        )
        btn_lang.bind(on_press=self._toggle_lang)
        row.add_widget(btn_lang)

        btn_about = Button(
            text=T("about_btn"),
            size_hint=(None, None), size=(dp(160), dp(26)),
            background_normal="", background_color=(0.25, 0.28, 0.35, 1),
            color=TEXT_PRI, font_size=sp(9), bold=True,
        )
        btn_about.bind(on_press=self._show_about)
        row.add_widget(btn_about)

        hdr.add_widget(row)
        return hdr

    def _show_about(self, *_):
        about = AboutPopup(on_dismiss=self._close_about,
                           size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self._about = about
        self.add_widget(about)

    def _close_about(self):
        if hasattr(self, "_about") and self._about.parent:
            self.remove_widget(self._about)

    def _toggle_lang(self, *_):
        _c.LANG = "en" if _c.LANG == "fr" else "fr"
        folder_save  = self._folder
        self._build()
        if folder_save:
            self._folder = folder_save
            disp = folder_save if len(folder_save) <= 42 else "\u2026" + folder_save[-40:]
            self.lbl_folder.text  = disp
            self.lbl_folder.color = TEXT_PRI

    def _make_card_folder(self):
        card = CardBox()
        card.add_widget(H2(text=T("folder")))
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self.lbl_folder = Label(
            text=T("no_folder"), color=TEXT_DIM, font_size=sp(12),
            halign="left", valign="middle", size_hint_x=0.72,
        )
        self.lbl_folder.bind(size=lambda *_: setattr(
            self.lbl_folder, "text_size", self.lbl_folder.size))
        btn = Btn(text=T("browse"), color=ACCENT2, size_hint_x=0.28, height=dp(36))
        btn.bind(on_press=lambda *_: FolderPopup(self._set_folder).open())
        row.add_widget(self.lbl_folder); row.add_widget(btn)
        card.add_widget(row)
        return card

    def _make_card_resolution(self):
        card = CardBox()
        card.add_widget(H2(text=T("resolution")))
        row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        self._res_btns = {}
        for key in RES_KEYS:
            btn = Button(
                text=T(f"res_{key}"),
                size_hint=(1, 1),
                background_normal="", font_size=sp(12), bold=True,
            )
            btn.bind(on_press=lambda b, k=key: self._select_res(k, b))
            row.add_widget(btn)
            self._res_btns[key] = btn
        card.add_widget(row)
        self._update_radio_colors(self._res_btns, self._res_key)
        return card

    def _select_res(self, key, btn):
        self._res_key = key
        self._update_radio_colors(self._res_btns, key)
        self._update_summary()

    def _select_quality(self, key, btn):
        self._quality_key = key
        self._update_radio_colors(self._quality_btns, key)
        self._update_summary()

    def _update_radio_colors(self, btns, selected_key):
        for k, btn in btns.items():
            active = (k == selected_key)
            if active and k == "off":
                btn.background_color = (0.50, 0.45, 0.35, 1)
            else:
                btn.background_color = ACCENT if active else (0.18, 0.22, 0.28, 1)
            btn.color = (1, 1, 1, 1)

    def _make_card_quality(self):
        card = CardBox()
        card.add_widget(H2(text=T("compression")))
        row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        self._quality_btns = {}
        for key in QUALITY_KEYS:
            btn = Button(
                text=T(f"q_{key}"),
                size_hint=(1, 1),
                background_normal="", font_size=sp(12), bold=True,
            )
            btn.bind(on_press=lambda b, k=key: self._select_quality(k, b))
            row.add_widget(btn)
            self._quality_btns[key] = btn
        card.add_widget(row)

        sub_row = BoxLayout(size_hint_y=None, height=dp(16), spacing=dp(6))
        for key in QUALITY_KEYS:
            sub_text = (T(f"q_{key}_sub") if key != "off" else "")
            sub_row.add_widget(Sub(
                text=sub_text, halign="center" if sub_text else "left",
                color=TEXT_DIM,
            ))
        card.add_widget(sub_row)
        self._update_radio_colors(self._quality_btns, self._quality_key)
        return card

    def _update_summary(self):
        res_px = RES_LEVELS[self._res_key]
        if self._quality_key == "off":
            t = f"{res_px} px max  \u2022  {T('quality_kept')}"
        else:
            pct = QUALITY_LEVELS[self._quality_key]
            t = f"{res_px} px max  \u2022  {T(f'q_{self._quality_key}')}  {pct} %"
        self.lbl_summary.text = t

    def _make_btn_row(self):
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        self.btn_scan  = Btn(text=T("scan"),  color=ACCENT2)
        self.btn_start = Btn(text=T("start"), color=SUCCESS)
        self.btn_start.disabled = True
        self.btn_scan.bind( on_press=self._scan)
        self.btn_start.bind(on_press=self._start)
        row.add_widget(self.btn_scan); row.add_widget(self.btn_start)
        return row

    def _make_card_progress(self):
        card = CardBox()
        self.lbl_status = Sub(text=T("waiting"), halign="left",
                              size_hint_y=None, height=dp(20))
        self.progress = ProgressBar(max=100, value=0,
                                    size_hint_y=None, height=dp(12))
        card.add_widget(self.lbl_status)
        card.add_widget(self.progress)
        return card

    def _make_card_thumbs(self):
        card = CardBox()
        self._lbl_thumbs_title = H2(text=f"{T('preview')} (0)")
        card.add_widget(self._lbl_thumbs_title)

        self._thumb_sv = ScrollView(
            size_hint_y=None, height=CARD_H + dp(4),
            do_scroll_x=True, do_scroll_y=False,
        )
        self._thumb_row = BoxLayout(
            orientation="horizontal", size_hint=(None, 1), spacing=dp(6),
        )
        self._thumb_row.bind(minimum_width=self._thumb_row.setter("width"))
        self._thumb_sv.add_widget(self._thumb_row)
        card.add_widget(self._thumb_sv)

        self._lbl_empty = Sub(
            text=T("thumb_wait"), halign="center", color=TEXT_DIM,
            size_hint_y=None, height=dp(20),
        )
        card.add_widget(self._lbl_empty)
        return card

    def _make_ad_section(self):
        card = CardBox()

        card.add_widget(H2(text=T("sg_ad_title"), color=ACCENT))
        card.add_widget(Label(
            text=T("sg_ad_desc"), color=TEXT_SEC, font_size=sp(11),
            size_hint_y=None, height=dp(36), halign="left", valign="middle",
        ))
        btn_ad = Btn(text="🔗  " + T("sg_ad_link"), color=ACCENT2, height=dp(40))
        btn_ad.bind(on_press=lambda *_: webbrowser.open(
            _c._TR.get(_c.LANG, _c._TR["en"]).get("sg_ad_link",
            _c._TR["en"]["sg_ad_link"])))
        card.add_widget(btn_ad)

        card.add_widget(Label(size_hint_y=None, height=dp(4)))

        card.add_widget(H2(text=T("sg_desktop_title"), color=DONATION))
        card.add_widget(Label(
            text=T("sg_desktop_desc"), color=TEXT_SEC, font_size=sp(11),
            size_hint_y=None, height=dp(36), halign="left", valign="middle",
        ))
        btn_desk = Btn(text="🔗  " + T("sg_desktop_link"), color=DONATION, height=dp(40))
        btn_desk.bind(on_press=lambda *_: webbrowser.open(
            _c._TR.get(_c.LANG, _c._TR["en"]).get("sg_desktop_link",
            _c._TR["en"]["sg_desktop_link"])))
        card.add_widget(btn_desk)

        card.add_widget(Label(
            text=T("privacy"), color=TEXT_DIM, font_size=sp(10),
            size_hint_y=None, height=dp(36), halign="center", valign="middle",
        ))
        card.add_widget(Label(
            text=T("contact").format(email=CONTACT_EMAIL),
            color=TEXT_DIM, font_size=sp(11),
            size_hint_y=None, height=dp(20), halign="center",
        ))
        return card

    def _add_thumb(self, info):
        n = len(self._thumb_cards)
        if n >= MAX_THUMBS or info["path"] in self._thumb_cards:
            return
        if n == 0 and self._lbl_empty.parent:
            self._lbl_empty.parent.remove_widget(self._lbl_empty)

        card = ThumbCard(info)
        self._thumb_cards[info["path"]] = card
        self._thumb_row.add_widget(card)

        shown = len(self._thumb_cards)
        total = len(self._images) if self._images else shown
        extra = f"  {T('first30')}" if total > MAX_THUMBS else ""
        self._lbl_thumbs_title.text = f"{T('preview')}  \u2013  {shown}{extra}"
        Clock.schedule_once(
            lambda dt: setattr(self._thumb_sv, "scroll_x", 1.0), 0.05)

    def _reset_thumbs(self):
        self._thumb_row.clear_widgets()
        self._thumb_cards.clear()
        self._lbl_thumbs_title.text = f"{T('preview')} (0)"
        parent = self._thumb_sv.parent
        if self._lbl_empty not in parent.children:
            parent.add_widget(self._lbl_empty)

    def _set_folder(self, path):
        self._folder = path
        disp = path if len(path) <= 42 else "\u2026" + path[-40:]
        self.lbl_folder.text  = disp
        self.lbl_folder.color = TEXT_PRI
        self._images = []
        self.btn_start.disabled = True
        self._reset_thumbs()

    def _scan(self, *_):
        if not self._folder:
            return
        self.btn_scan.disabled  = True
        self.btn_start.disabled = True
        self.btn_start.background_color = (0.20, 0.22, 0.28, 1)
        self._images = []
        self._reset_thumbs()
        self.lbl_status.text  = T("scanning")
        self.lbl_status.color = TEXT_SEC
        self.progress.value   = 0

        def on_found(info):
            Clock.schedule_once(lambda dt, i=info: self._add_thumb(i))

        def run():
            images = collect_images(self._folder, self._res_key, self._quality_key, on_found=on_found)
            Clock.schedule_once(lambda dt: self._on_scan_done(images))

        threading.Thread(target=run, daemon=True).start()

    def _on_scan_done(self, images):
        self._images = images
        self.btn_scan.disabled = False
        n = len(images)
        if n == 0:
            self.lbl_status.text = T("no_image")
            self.lbl_status.color = WARNING
            self.btn_start.disabled = True
            self.btn_start.background_color = (0.20, 0.22, 0.28, 1)
        else:
            to_process = sum(1 for i in images if i.get("skip_reason") is None)
            already_opt = n - to_process
            total_ko = sum(i["size_ko"] for i in images)
            size_str = f"{total_ko/1024:.1f} Mo" if total_ko >= 1024 else f"{total_ko} Ko"
            if to_process == 0:
                self.lbl_status.text = (
                    f"{T('all_opt')} ({n})  \u2022  {size_str}"
                )
                self.btn_start.disabled = True
                self.btn_start.text = T("nothing_to_do")
                self.btn_start.background_color = (0.20, 0.22, 0.28, 1)
            else:
                if already_opt > 0:
                    self.lbl_status.text = (
                        f"{T('to_process')} {to_process} / {T('already_opt')} {already_opt}  \u2022  {size_str}"
                    )
                else:
                    self.lbl_status.text = f"{n} {T('found')}  \u2022  {size_str}"
                self.btn_start.text = T("preview_launch").format(n=n)
                self.btn_start.disabled = False
                self.btn_start.background_color = SUCCESS
            self.lbl_status.color = TEXT_SEC

    def _show_preview(self, *_):
        if not self._images:
            return
        preview = PreviewScreen(
            self._images, self._res_key, self._quality_key, self._folder,
            on_launch=self._start_processing,
            on_back=self._close_preview,
            size_hint=(1, 1), pos_hint={"x": 0, "y": 0},
        )
        self._preview = preview
        self.add_widget(preview)

    def _close_preview(self):
        if hasattr(self, "_preview") and self._preview.parent:
            self.remove_widget(self._preview)

    def _start(self, *_):
        if not self._images:
            return
        self._show_preview()

    def _start_processing(self):
        self._close_preview()
        if not self._images:
            return
        self.btn_scan.disabled  = True
        self.btn_start.disabled = True
        self.btn_start.background_color = (0.20, 0.22, 0.28, 1)
        self._cancelled = False

        total   = len(self._images)
        self.progress.max   = total
        self.progress.value = 0
        stats = {"ok": 0, "err": 0, "before_ko": 0, "after_ko": 0}

        stats["skipped"] = 0
        def run():
            for i, info in enumerate(list(self._images)):
                if self._cancelled:
                    break
                Clock.schedule_once(
                    lambda dt, inf=info: self._thumb_set_processing(inf))
                time.sleep(0.05)
                result = process_image(info, self._res_key, self._quality_key)
                stats["before_ko"] += result["size_before_ko"]
                stats["after_ko"]  += result["size_after_ko"]
                if result.get("skipped"):
                    stats["skipped"] += 1
                elif result["ok"]:
                    stats["ok"] += 1
                else:
                    stats["err"] += 1
                Clock.schedule_once(
                    lambda dt, inf=info, res=result, idx=i+1:
                    self._on_img_done(inf, res, idx, total)
                )
                time.sleep(0.03)
            Clock.schedule_once(lambda dt: self._on_done(stats, total))

        threading.Thread(target=run, daemon=True).start()

    def _thumb_set_processing(self, info):
        card = self._thumb_cards.get(info["path"])
        if card:
            card.set_processing()

    def _on_img_done(self, info, result, idx, total):
        self.progress.value = idx
        pct = int(idx / total * 100)
        self.lbl_status.text = f"{T('processing')} {idx}/{total}  ({pct} %)"
        card = self._thumb_cards.get(info["path"])
        if card:
            card.set_done(result["ok"], result.get("size_after_ko", 0),
                         result.get("error", ""))

    def _on_done(self, stats, total):
        self.btn_scan.disabled  = False
        self.btn_start.disabled = False
        saved = stats["before_ko"] - stats["after_ko"]
        skipped_n = stats.get("skipped", 0)
        txt = (
            f"{T('done')}  \u2022  {stats['ok']}/{total} {T('treated')}  \u2022  "
            f"-{saved} {T('saved_ko')}"
        )
        if skipped_n:
            txt += f"  \u2022  {skipped_n} {T('already_opt')}"
        self.lbl_status.text = txt
        self._images = []
        report = ReportScreen(
            n_ok=stats["ok"], n_err=stats["err"],
            skipped=skipped_n,
            before_ko=stats["before_ko"], after_ko=stats["after_ko"],
            folder=self._folder, on_close=self._close_report,
            size_hint=(1, 1), pos_hint={"x": 0, "y": 0},
        )
        self._report = report
        self.add_widget(report)

    def _close_report(self):
        if hasattr(self, "_report") and self._report.parent:
            self.remove_widget(self._report)
