try:
    from android.permissions import request_permissions, check_permission, Permission
    from android import api_version as ANDROID_API
    _ON_ANDROID = True
except ImportError:
    _ON_ANDROID = False
    ANDROID_API = 0

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.label import Label

from bulkresizer.constants import BG_DARK, ICON_PATH, T, DANGER
from bulkresizer.ui import MainScreen

class ImageOptimizerApp(App):
    def build(self):
        self.title = T("app_title")
        self.icon  = ICON_PATH
        Window.clearcolor = BG_DARK
        return MainScreen()

    def on_start(self):
        if not _ON_ANDROID:
            return
        if self._request_storage_perms():
            return
        self._request_manage_storage()

    def _request_storage_perms(self):
        api = ANDROID_API
        if api >= 33:
            perms = [Permission.READ_MEDIA_IMAGES]
        elif api >= 30:
            perms = [Permission.READ_EXTERNAL_STORAGE,
                     Permission.WRITE_EXTERNAL_STORAGE]
        else:
            perms = [Permission.READ_EXTERNAL_STORAGE,
                     Permission.WRITE_EXTERNAL_STORAGE]
        needed = [p for p in perms if p and not check_permission(p)]
        if needed:
            request_permissions(needed, self._on_permissions)
            return True
        return False

    def _request_manage_storage(self):
        if ANDROID_API < 30:
            return
        try:
            from android import mActivity
            if check_permission(Permission.MANAGE_EXTERNAL_STORAGE):
                return
            from jnius import autoclass
            uri = "package:" + mActivity.getPackageName()
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            i = Intent()
            i.setAction("android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION")
            i.setData(Uri.parse(uri))
            mActivity.startActivity(i)
        except Exception:
            pass

    def _on_permissions(self, permissions, results):
        if not all(results):
            p = Popup(
                title=T("perm_denied"),
                content=Label(text=T("perm_msg"), halign="center"),
                size_hint=(0.85, 0.35),
                background_color=BG_DARK, title_color=DANGER,
            )
            p.open()
            return
        self._request_manage_storage()
