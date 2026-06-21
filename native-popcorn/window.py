import sys
import threading
import gi
import database

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf
import urllib.request
import os
import hashlib

import api
import player

cache_dir_base = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
IMAGE_CACHE_DIR = os.path.join(cache_dir_base, 'native-popcorn', 'images')
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

def load_image_into_picture(url, picture_widget, width=None, height=None):
    if not url: return
    
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_file = os.path.join(IMAGE_CACHE_DIR, url_hash)
    
    def fetch_image():
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    data = f.read()
                GLib.idle_add(set_image_from_data, data, picture_widget, width, height)
                return
                
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = response.read()
                
            with open(cache_file, 'wb') as f:
                f.write(data)
                
            GLib.idle_add(set_image_from_data, data, picture_widget, width, height)
        except Exception as e:
            print(f"Failed to load image: {e}")
    threading.Thread(target=fetch_image, daemon=True).start()

def set_image_from_data(data, picture_widget, width=None, height=None):
    try:
        loader = GdkPixbuf.PixbufLoader()
        loader.write(data)
        loader.close()
        if pixbuf := loader.get_pixbuf():
            if width and height:
                pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
            picture_widget.set_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
            picture_widget.set_can_shrink(True)
    except Exception as e:
        print(f"Failed to set image: {e}")

class MovieDetailsPage(Gtk.Overlay):
    def __init__(self, movie, on_back):
        super().__init__()
        self.movie_stub = movie
        self.media_type = movie.get("type", "movie")
        self.selected_season = None
        self.selected_episode = None
        self.torrents = []
        
        self.backdrop_pic = Gtk.Picture()
        self.backdrop_pic.set_can_shrink(True)
        self.backdrop_pic.set_opacity(0.3)
        self.set_child(self.backdrop_pic)
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.main_box.set_css_classes(['backdrop-overlay'])
        self.add_overlay(self.main_box)
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_margin_start(16)
        header_box.set_margin_top(16)
        
        back_btn = Gtk.Button(icon_name="go-previous-symbolic")
        back_btn.set_tooltip_text("Back")
        back_btn.set_css_classes(['circular', 'flat'])
        back_btn.connect("clicked", lambda x: on_back())
        header_box.append(back_btn)
        
        self.main_box.append(header_box)
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.content_box.set_margin_start(48)
        self.content_box.set_margin_end(48)
        self.content_box.set_margin_top(24)
        self.content_box.set_margin_bottom(24)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.content_box)
        scrolled.add_css_class("transparent")
        
        self.inner_stack = Gtk.Stack()
        self.inner_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.inner_stack.add_named(scrolled, "details")
        self.main_box.append(self.inner_stack)
        
        self.build_download_ui()
        
        self.spinner = Gtk.Spinner()
        self.spinner.start()
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.set_valign(Gtk.Align.CENTER)
        self.spinner.set_vexpand(True)
        self.content_box.append(self.spinner)
        
        self.progress_label = Gtk.Label(label="")
        self.progress_label.set_halign(Gtk.Align.START)
        
        self.load_details_async()
        
    def build_download_ui(self):
        self.dl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.dl_box.set_valign(Gtk.Align.CENTER)
        self.dl_box.set_halign(Gtk.Align.CENTER)
        self.dl_box.set_vexpand(True)
        self.dl_box.set_margin_start(24)
        self.dl_box.set_margin_end(24)
        
        self.dl_title = Gtk.Label(label="")
        self.dl_title.set_css_classes(['title-1'])
        self.dl_title.set_wrap(True)
        self.dl_title.set_halign(Gtk.Align.CENTER)
        self.dl_box.append(self.dl_title)
        
        self.dl_progress = Gtk.ProgressBar()
        self.dl_progress.set_size_request(500, -1)
        self.dl_box.append(self.dl_progress)
        
        self.dl_status = Gtk.Label(label="Initializing...")
        self.dl_status.set_css_classes(['title-2'])
        self.dl_box.append(self.dl_status)
        
        self.dl_stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.dl_stats_box.set_css_classes(['pt-card'])
        self.dl_stats_box.set_margin_start(48)
        self.dl_stats_box.set_margin_end(48)
        self.dl_stats_box.set_margin_top(12)
        self.dl_stats_box.set_margin_bottom(12)
        
        self.dl_percent = Gtk.Label(label="0%")
        self.dl_percent.set_css_classes(['title-3'])
        self.dl_stats_box.append(self.dl_percent)
        
        self.dl_speed = Gtk.Label(label="")
        self.dl_stats_box.append(self.dl_speed)
        
        self.dl_peers = Gtk.Label(label="")
        self.dl_stats_box.append(self.dl_peers)
        
        self.dl_box.append(self.dl_stats_box)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.set_css_classes(['pill', 'suggested-action'])
        cancel_btn.set_size_request(120, -1)
        cancel_btn.set_halign(Gtk.Align.CENTER)
        cancel_btn.connect("clicked", self.on_cancel_download)
        self.dl_box.append(cancel_btn)
        
        self.inner_stack.add_named(self.dl_box, "download")
        
    def on_cancel_download(self, btn):
        print(f"DEBUG: on_cancel_download called. Current selected_torrent is: {getattr(self, 'selected_torrent', None)}")
        player.stop_player()
        self.inner_stack.set_visible_child_name("details")
        self.watch_btn.set_sensitive(True)
        self.progress_label.set_text("")
        
        # GTK4 DropDown bug workaround: restore selection state after Stack unmap
        if hasattr(self, 'file_dropdown') and hasattr(self, 'current_t_list') and hasattr(self, 'selected_torrent'):
            try:
                idx = self.current_t_list.index(self.selected_torrent)
                print(f"DEBUG: Restoring file_dropdown to idx {idx}")
                self.file_dropdown.set_selected(idx)
            except ValueError:
                print("DEBUG: ValueError when trying to restore file_dropdown selection")
        
    def load_details_async(self):
        def fetch():
            details = api.fetch_movie_details(self.movie_stub.get("id"), self.media_type)
            torrents = []
            if self.media_type != "series":
                torrents = api.get_torrents(self.movie_stub.get("id"), self.media_type)
            GLib.idle_add(self.build_ui, details, torrents)
        threading.Thread(target=fetch, daemon=True).start()
        
    def toggle_favorite(self, details):
        item_id = details.get("id")
        if database.is_favorite(item_id):
            database.remove_favorite(item_id)
            self.detail_fav_btn.set_label("♡ Add to Favorites")
        else:
            database.add_favorite({
                "id": item_id,
                "title": details.get("title"),
                "year": details.get("year"),
                "medium_cover_image": details.get("medium_cover_image"),
                "type": self.media_type
            })
            self.detail_fav_btn.set_label("♥ Remove from Favorites")
            
    def toggle_watched(self, details):
        item_id = details.get("id")
        if database.is_watched(item_id):
            database.remove_watched(item_id)
            self.detail_seen_btn.set_label("👁 Not Seen")
        else:
            database.add_watched({
                "id": item_id,
                "title": details.get("title"),
                "year": details.get("year"),
                "medium_cover_image": details.get("medium_cover_image"),
                "type": self.media_type
            })
            self.detail_seen_btn.set_label("👁 Seen")
        
    def build_ui(self, details, torrents):
        self.content_box.remove(self.spinner)
        if not details:
            self.content_box.append(Gtk.Label(label="Failed to load details."))
            return
            
        if details.get("background"):
            load_image_into_picture(details.get("background"), self.backdrop_pic)
            
        top_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=32)
        
        poster = Gtk.Picture()
        poster.set_size_request(250, 375)
        poster.set_valign(Gtk.Align.START)
        top_hbox.append(poster)
        load_image_into_picture(details.get("medium_cover_image"), poster)
        
        info_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        title = Gtk.Label(label=details.get("title", ""))
        title.set_css_classes(['title-1'])
        title.set_halign(Gtk.Align.START)
        title.set_wrap(True)
        info_vbox.append(title)
        
        meta_str = f"{details.get('year', '')} • {details.get('runtime', '')} • {details.get('genre', '')} • IMDb {details.get('imdbRating', '')}"
        meta = Gtk.Label(label=meta_str)
        meta.set_halign(Gtk.Align.START)
        meta.set_css_classes(['dim-label'])
        info_vbox.append(meta)
        
        desc = Gtk.Label(label=details.get("description", ""))
        desc.set_wrap(True)
        desc.set_halign(Gtk.Align.START)
        desc.set_max_width_chars(80)
        desc.set_margin_top(16)
        desc.set_margin_bottom(16)
        info_vbox.append(desc)
        
        # Row 1: Actions (Fav, Seen, Trailer)
        self.row1_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.row1_box.set_margin_top(16)
        
        item_id = details.get("id")
        self.detail_fav_btn = Gtk.Button(label="♥ Remove from Favorites" if database.is_favorite(item_id) else "♡ Add to Favorites")
        self.detail_fav_btn.set_css_classes(['pill'])
        self.detail_fav_btn.connect("clicked", lambda x: self.toggle_favorite(details))
        self.row1_box.append(self.detail_fav_btn)
        
        self.detail_seen_btn = Gtk.Button(label="👁 Seen" if database.is_watched(item_id) else "👁 Not Seen")
        self.detail_seen_btn.set_css_classes(['pill'])
        self.detail_seen_btn.connect("clicked", lambda x: self.toggle_watched(details))
        self.row1_box.append(self.detail_seen_btn)
        
        trailer_btn = Gtk.Button()
        trailer_icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
        trailer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        trailer_box.append(trailer_icon)
        trailer_box.append(Gtk.Label(label="Watch Trailer"))
        trailer_btn.set_child(trailer_box)
        trailer_btn.set_css_classes(['pill'])
        trailer_btn.set_valign(Gtk.Align.CENTER)
        trailer_btn.connect("clicked", lambda x: self.on_trailer_clicked(details.get("trailer")))
        if not details.get("trailer"): trailer_btn.set_sensitive(False)
        self.row1_box.append(trailer_btn)
        
        info_vbox.append(self.row1_box)
        
        # Row 2: Series Selection (if applicable) & Qualities
        self.row2_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.row2_box.set_margin_top(16)
        
        if self.media_type in ["series", "anime"] and details.get("videos"):
            videos = details.get("videos")
            seasons = sorted(list(set([v.get("season", 1) for v in videos])))
            
            self.season_dropdown = Gtk.DropDown.new_from_strings([f"Season {s}" for s in seasons])
            self.season_dropdown.set_valign(Gtk.Align.CENTER)
            self.row2_box.append(self.season_dropdown)
            
            self.episode_dropdown = Gtk.DropDown.new_from_strings([])
            self.episode_dropdown.set_valign(Gtk.Align.CENTER)
            self.row2_box.append(self.episode_dropdown)
            
            def on_season_changed(dropdown, *args):
                idx = dropdown.get_selected()
                if idx == Gtk.INVALID_LIST_POSITION: return
                s = seasons[idx]
                if getattr(self, 'selected_season', None) == s:
                    return
                self.selected_season = s
                eps = [v for v in videos if v.get("season") == s]
                eps.sort(key=lambda x: x.get("episode", 0))
                self.current_episodes = eps
                ep_strings = [f"Ep {e.get('episode')}: {e.get('title') or e.get('name', '')}" for e in eps]
                self.episode_dropdown.set_model(Gtk.StringList.new(ep_strings))
                self.episode_dropdown.set_selected(0)
                
            self.season_dropdown.connect("notify::selected", on_season_changed)
            
            def on_episode_changed(dropdown, *args):
                idx = dropdown.get_selected()
                if idx == Gtk.INVALID_LIST_POSITION: return
                ep = self.current_episodes[idx].get("episode")
                if getattr(self, 'selected_episode', None) == ep:
                    return
                self.selected_episode = ep
                self.fetch_torrents_async()
                
            self.episode_dropdown.connect("notify::selected", on_episode_changed)
            if seasons: on_season_changed(self.season_dropdown)
            
        self.quality_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.quality_button_box.set_valign(Gtk.Align.CENTER)
        self.row2_box.append(self.quality_button_box)
        
        info_vbox.append(self.row2_box)
        
        # Row 3: Dropdown & Watch/Download
        self.row3_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.row3_box.set_margin_top(12)
        
        self.file_dropdown = Gtk.DropDown.new_from_strings([])
        self.file_dropdown.set_valign(Gtk.Align.CENTER)
        
        def on_dropdown_changed(dropdown, pspec):
            idx = dropdown.get_selected()
            print(f"DEBUG: on_dropdown_changed fired with idx {idx}")
            if hasattr(self, 'current_t_list') and idx != Gtk.INVALID_LIST_POSITION and idx < len(self.current_t_list):
                new_torrent = self.current_t_list[idx]
                if getattr(self, 'selected_torrent', None) == new_torrent:
                    return
                self.selected_torrent = new_torrent
                print(f"DEBUG: selected_torrent updated to {new_torrent}")
                
        self.file_dropdown.connect("notify::selected", on_dropdown_changed)
        self.row3_box.append(self.file_dropdown)
        
        self.watch_btn = Gtk.Button(label="WATCH IT NOW")
        self.watch_btn.set_css_classes(['suggested-action', 'pill'])
        self.watch_btn.set_size_request(150, 40)
        self.watch_btn.connect("clicked", self.on_watch_clicked)
        self.row3_box.append(self.watch_btn)
        
        self.download_btn = Gtk.Button(label="Download")
        self.download_btn.set_css_classes(['pill'])
        self.download_btn.set_valign(Gtk.Align.CENTER)
        self.download_btn.connect("clicked", self.on_download_clicked)
        self.row3_box.append(self.download_btn)
        
        info_vbox.append(self.row3_box)
        info_vbox.append(self.progress_label)
        
        top_hbox.append(info_vbox)
        self.content_box.append(top_hbox)
        
        if self.media_type != "series":
            self.torrents = torrents
            self.update_quality_dropdown()
            
    def fetch_torrents_async(self):
        if hasattr(self, 'watch_btn') and self.watch_btn:
            self.watch_btn.set_sensitive(False)
        if hasattr(self, 'download_btn') and self.download_btn:
            self.download_btn.set_sensitive(False)
        if hasattr(self, 'progress_label') and self.progress_label:
            self.progress_label.set_text("Loading streams...")
        
        if hasattr(self, 'quality_button_box') and self.quality_button_box:
            while child := self.quality_button_box.get_first_child():
                self.quality_button_box.remove(child)
        if hasattr(self, 'file_dropdown') and self.file_dropdown:
            self.file_dropdown.set_model(Gtk.StringList.new(["Loading..."]))
        
        def fetch():
            torrents = api.get_torrents(self.movie_stub.get("id"), self.media_type, self.selected_season, self.selected_episode)
            GLib.idle_add(self.on_torrents_fetched, torrents)
        threading.Thread(target=fetch, daemon=True).start()
        
    def on_torrents_fetched(self, torrents):
        self.progress_label.set_text("")
        self.torrents = torrents
        self.update_quality_dropdown()
        
    def update_quality_dropdown(self):
        while child := self.quality_button_box.get_first_child():
            self.quality_button_box.remove(child)
            
        if not self.torrents:
            self.watch_btn.set_sensitive(False)
            self.download_btn.set_sensitive(False)
            self.file_dropdown.set_model(Gtk.StringList.new(["No streams"]))
            return
            
        self.watch_btn.set_sensitive(True)
        self.download_btn.set_sensitive(True)
        
        quality_groups = {"4K": [], "2160p": [], "1080p": [], "720p": [], "More": []}
        
        for t in self.torrents:
            q = t.get('quality', 'Unknown').upper()
            if "4K" in q: quality_groups["4K"].append(t)
            elif "2160" in q: quality_groups["2160p"].append(t)
            elif "1080" in q: quality_groups["1080p"].append(t)
            elif "720" in q: quality_groups["720p"].append(t)
            else: quality_groups["More"].append(t)
            
        self.selected_torrent = None
        self.quality_buttons = []
        self.current_t_list = []
        
        def on_quality_btn_clicked(btn, t_list):
            for b in self.quality_buttons:
                b.set_css_classes(['pill'])
            btn.set_css_classes(['pill', 'suggested-action'])
            
            self.current_t_list = t_list
            self.selected_torrent = t_list[0]
            strings = [f"{t.get('size', 'Unknown')} ({t.get('seeders', 0)} seeds)" for t in t_list]
            self.file_dropdown.set_model(Gtk.StringList.new(strings))
            self.file_dropdown.set_selected(0)
            
        first_btn = None
        first_t_list = None
        for q_label in ["4K", "2160p", "1080p", "720p", "More"]:
            t_list = quality_groups[q_label]
            if t_list:
                btn = Gtk.Button(label=q_label)
                btn.set_css_classes(['pill'])
                btn.connect("clicked", on_quality_btn_clicked, t_list)
                self.quality_buttons.append(btn)
                self.quality_button_box.append(btn)
                if not first_btn:
                    first_btn = btn
                    first_t_list = t_list
                    
        if first_btn:
            on_quality_btn_clicked(first_btn, first_t_list)
            
    def on_download_clicked(self, btn):
        if hasattr(self, 'file_dropdown') and hasattr(self, 'current_t_list') and self.current_t_list:
            idx = self.file_dropdown.get_selected()
            if idx != Gtk.INVALID_LIST_POSITION and idx < len(self.current_t_list):
                self.selected_torrent = self.current_t_list[idx]
                
        if not hasattr(self, 'selected_torrent') or not self.selected_torrent:
            return
        magnet = self.selected_torrent.get("url") or self.selected_torrent.get("magnet")
        if not magnet and self.selected_torrent.get("hash"):
            magnet = api.build_magnet(self.selected_torrent.get("hash"), self.movie_stub.get("title", ""))
        if magnet:
            import subprocess
            subprocess.Popen(['xdg-open', magnet])
        
    def on_watch_clicked(self, btn):
        print(f"DEBUG: on_watch_clicked. file_dropdown.get_selected() = {self.file_dropdown.get_selected() if hasattr(self, 'file_dropdown') else 'N/A'}")
        if hasattr(self, 'file_dropdown') and hasattr(self, 'current_t_list') and self.current_t_list:
            idx = self.file_dropdown.get_selected()
            if idx != Gtk.INVALID_LIST_POSITION and idx < len(self.current_t_list):
                self.selected_torrent = self.current_t_list[idx]
                print(f"DEBUG: Force synced selected_torrent in on_watch_clicked to {self.selected_torrent}")
                
        if not hasattr(self, 'selected_torrent') or not self.selected_torrent:
            print("DEBUG: Watch it now failed! selected_torrent is None or missing.")
            if hasattr(self, 'progress_label') and self.progress_label:
                self.progress_label.set_text("No streams available.")
            return
            
        import urllib.parse
        torrent = self.selected_torrent
        magnet = torrent.get("url") or torrent.get("magnet")
        if not magnet and torrent.get("hash"):
            magnet = api.build_magnet(torrent.get("hash"), self.movie_stub.get("title", ""))
            
        if magnet and magnet.startswith("magnet:?"):
            trackers = [
                "udp://tracker.opentrackr.org:1337/announce",
                "udp://tracker.openbittorrent.com:80/announce",
                "udp://tracker.torrent.eu.org:451/announce",
                "udp://exodus.desync.com:6969/announce",
                "udp://explodie.org:6969/announce",
                "udp://p4p.arenabg.com:1337/announce",
                "udp://tracker.internetwarriors.net:1337/announce",
                "udp://tracker.cyberia.is:6969/announce",
                "http://tracker.openbittorrent.com:80/announce",
                "udp://open.stealth.si:80/announce"
            ]
            for tr in trackers:
                encoded_tr = urllib.parse.quote(tr, safe="")
                if encoded_tr not in magnet:
                    magnet += f"&tr={encoded_tr}"
        
        self.inner_stack.set_visible_child_name("download")
        self.watch_btn.set_sensitive(False)
        self.progress_label.set_text("")
        self.dl_status.set_text("Starting stream...")
        self.dl_progress.set_fraction(0.0)
        self.dl_percent.set_text("0%")
        self.dl_speed.set_text("")
        self.dl_peers.set_text("")
        
        title_str = self.movie_stub.get("title", "")
        if self.media_type == "series":
            title_str += f" - Season {self.selected_season}, Ep {self.selected_episode}"
        self.dl_title.set_text(title_str)
        
        def progress_cb(status_data):
            if type(status_data) == dict:
                if status_data.get("closed"):
                    self.on_cancel_download(None)
                    return
                    
                if status_data.get("status"):
                    self.dl_status.set_text(status_data["status"])
                    
                if "downloaded" in status_data and "totalLength" in status_data:
                    dl = status_data["downloaded"]
                    tot = status_data["totalLength"]
                    if tot > 0:
                        frac = dl / tot
                        self.dl_progress.set_fraction(frac)
                        self.dl_percent.set_text(f"{frac*100:.1f}% ({dl/(1024*1024):.2f} MiB / {tot/(1024*1024*1024):.2f} GiB)")
                        
                if "downloadSpeed" in status_data:
                    speed = status_data["downloadSpeed"] / 1024
                    self.dl_speed.set_text(f"Download: {speed:.2f} KiB/s")
                    
                if "activePeers" in status_data:
                    self.dl_peers.set_text(f"Active Peers: {status_data['activePeers']} / {status_data.get('totalPeers', 0)}")
                    
            elif type(status_data) == str:
                self.dl_status.set_text(status_data)
                
            return False # Let GLib know we don't want to repeat this if it was a timeout, but we use idle_add anyway
            
        file_index = torrent.get("file_index")
        player.play_magnet(magnet, "mpv", progress_callback=progress_cb, file_index=file_index)
        
    def on_trailer_clicked(self, trailer_id):
        self.inner_stack.set_visible_child_name("download")
        self.watch_btn.set_sensitive(False)
        self.progress_label.set_text("")
        self.dl_status.set_text("Loading Trailer via YouTube...")
        self.dl_progress.set_fraction(0.0)
        self.dl_percent.set_text("")
        self.dl_speed.set_text("")
        self.dl_peers.set_text("")
        
        title_str = self.movie_stub.get("title", "") + " (Trailer)"
        self.dl_title.set_text(title_str)
        
        def progress_cb(status_data):
            if type(status_data) == dict:
                if status_data.get("closed"):
                    self.on_cancel_download(None)
                    return
                if status_data.get("status"):
                    self.dl_status.set_text(status_data["status"])
            elif type(status_data) == str:
                self.dl_status.set_text(status_data)
            return False
            
        player.play_trailer(trailer_id, progress_cb)

class MovieWidget(Gtk.Box):
    def __init__(self, movie, on_card_clicked):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.movie = movie
        
        # Match WineCharm icon view logic but make them slightly larger to fit ~15 per row
        self.set_size_request(130, 195)
        self.set_hexpand(True)
        self.set_halign(Gtk.Align.CENTER)
        self.set_css_classes(['pt-card'])
        
        icon_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        icon_container.set_hexpand(True)
        icon_container.set_halign(Gtk.Align.CENTER)
        
        self.overlay = Gtk.Overlay()
        self.poster_image = Gtk.Picture()
        self.poster_image.set_size_request(130, 195)
        self.overlay.set_child(self.poster_image)
        
        # Click event
        click = Gtk.GestureClick()
        click.connect("pressed", lambda gesture, n_press, x, y: on_card_clicked(self.movie))
        icon_container.add_controller(click)
        
        icon_container.append(self.overlay)
        self.append(icon_container)
        load_image_into_picture(movie.get("medium_cover_image"), self.poster_image, width=130, height=195)
        
        title_label = Gtk.Label(label=movie.get("title", "Unknown"))
        title_label.set_lines(1)
        import gi
        gi.require_version('Pango', '1.0')
        from gi.repository import Pango
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.set_max_width_chars(1)
        title_label.set_hexpand(True)
        title_label.set_halign(Gtk.Align.FILL)
        title_label.set_xalign(0.0)
        title_label.set_css_classes(['pt-card-title'])
        self.append(title_label)
        
        year_label = Gtk.Label(label=str(movie.get("year", "")))
        year_label.set_halign(Gtk.Align.START)
        year_label.set_css_classes(['pt-card-year'])
        self.append(year_label)

class NativePopcornWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Popcorn Time")
        self.set_default_size(1100, 800)
        self.connect("close-request", self.on_close_request)
        
        self.current_media_type = "movie"
        self.current_genre = "All"
        self.current_catalog_id = "trending"
        self.current_query = ""
        self.current_page = 1
        self.is_fetching = False

        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)
        
        # Topbar
        topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        topbar.set_css_classes(['topbar'])
        
        # Left side
        left_topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        self.movies_btn = Gtk.Button(label="Movies")
        self.movies_btn.set_css_classes(['topbar-item', 'selected'])
        self.movies_btn.connect("clicked", lambda x: self.switch_category("movie", "All", self.movies_btn))
        left_topbar.append(self.movies_btn)
        
        self.tv_btn = Gtk.Button(label="Series")
        self.tv_btn.set_css_classes(['topbar-item'])
        self.tv_btn.connect("clicked", lambda x: self.switch_category("series", "All", self.tv_btn))
        left_topbar.append(self.tv_btn)
        
        self.anime_btn = Gtk.Button(label="Anime")
        self.anime_btn.set_css_classes(['topbar-item'])
        self.anime_btn.connect("clicked", lambda x: self.switch_category("anime", "All", self.anime_btn))
        left_topbar.append(self.anime_btn)
        
        self.fav_btn = Gtk.Button(label="Favorites")
        self.fav_btn.set_css_classes(['topbar-item'])
        self.fav_btn.connect("clicked", lambda x: self.switch_category("favorites", "All", self.fav_btn))
        left_topbar.append(self.fav_btn)
        
        self.watched_btn = Gtk.Button(label="Watched")
        self.watched_btn.set_css_classes(['topbar-item'])
        self.watched_btn.connect("clicked", lambda x: self.switch_category("watched", "All", self.watched_btn))
        left_topbar.append(self.watched_btn)
        
        topbar.append(left_topbar)
        
        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        topbar.append(spacer)
        
        # Middle controls
        mid_topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mid_topbar.set_valign(Gtk.Align.CENTER)
        
        genre_label = Gtk.Label(label="Genre")
        genre_label.set_css_classes(['dim-label'])
        mid_topbar.append(genre_label)
        self.movie_genres = ["All", "Action", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery", "Romance", "Science Fiction", "TV Movie", "Thriller", "War", "Western"]
        self.anime_genres = ["All"]
        
        self.genre_dropdown = Gtk.DropDown.new_from_strings(self.movie_genres)
        self.genre_dropdown.set_valign(Gtk.Align.CENTER)
        self.genre_dropdown.connect("notify::selected", self.on_genre_changed)
        mid_topbar.append(self.genre_dropdown)
        
        sort_label = Gtk.Label(label="Sort by")
        sort_label.set_css_classes(['dim-label'])
        mid_topbar.append(sort_label)
        
        self.standard_sorts = ["Trending", "Popularity", "Last Added", "Year", "Title", "Rating"]
        self.anime_sorts = ["Trending", "Year", "Title"]
        self.sort_dropdown = Gtk.DropDown.new_from_strings(self.standard_sorts)
        self.sort_dropdown.set_valign(Gtk.Align.CENTER)
        self.sort_dropdown.connect("notify::selected", self.on_sort_changed)
        mid_topbar.append(self.sort_dropdown)
        
        topbar.append(mid_topbar)
        
        # Spacer
        spacer2 = Gtk.Box()
        spacer2.set_hexpand(True)
        topbar.append(spacer2)
        
        # Right controls
        right_topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        right_topbar.set_valign(Gtk.Align.CENTER)
        right_topbar.set_margin_end(16)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        right_topbar.append(self.search_entry)
        
        topbar.append(right_topbar)
        
        window_controls = Gtk.WindowControls(side=Gtk.PackType.END)
        topbar.append(window_controls)
        
        # Wrap topbar in WindowHandle to make it draggable
        window_handle = Gtk.WindowHandle()
        window_handle.set_child(topbar)
        toolbar_view.add_top_bar(window_handle)
        
        # Content Area (Stack)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        toolbar_view.set_content(self.stack)
        
        # Grid Page
        self.grid_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        vadjust = self.scrolled.get_vadjustment()
        vadjust.connect("value-changed", self.on_scroll)
        self.grid_page.append(self.scrolled)
        
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(100)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        # Tight spacing like WineCharm
        self.flowbox.set_column_spacing(8)
        self.flowbox.set_row_spacing(12)
        self.flowbox.set_margin_start(12)
        self.flowbox.set_margin_end(12)
        self.flowbox.set_margin_top(12)
        self.flowbox.set_margin_bottom(12)
        self.scrolled.set_child(self.flowbox)

        self.stack.add_named(self.grid_page, "grid")
        self.stack.set_visible_child_name("grid")
        
        self.load_movies()
        
    def switch_category(self, media_type, genre, btn):
        self.movies_btn.remove_css_class("selected")
        self.tv_btn.remove_css_class("selected")
        self.anime_btn.remove_css_class("selected")
        self.fav_btn.remove_css_class("selected")
        self.watched_btn.remove_css_class("selected")
        btn.add_css_class("selected")
        
        # Ensure we switch back to the grid view when a tab is clicked
        self.stack.set_visible_child_name("grid")
        
        # Update dropdown models based on category
        self.current_media_type = media_type
        self.current_genre = "All"
        self.current_catalog_id = "trending"
        
        if media_type == "anime":
            self.genre_dropdown.set_model(Gtk.StringList.new(self.anime_genres))
            self.sort_dropdown.set_model(Gtk.StringList.new(self.anime_sorts))
            self.genre_dropdown.set_sensitive(True)
            self.sort_dropdown.set_sensitive(True)
        elif media_type in ["favorites", "watched"]:
            # Disable filters for local lists
            self.genre_dropdown.set_sensitive(False)
            self.sort_dropdown.set_sensitive(False)
        else:
            self.genre_dropdown.set_model(Gtk.StringList.new(self.movie_genres))
            self.sort_dropdown.set_model(Gtk.StringList.new(self.standard_sorts))
            self.genre_dropdown.set_sensitive(True)
            self.sort_dropdown.set_sensitive(True)
            
        self.genre_dropdown.set_selected(0)
        self.sort_dropdown.set_selected(0)
            
        self.load_movies()
        
    def on_genre_changed(self, dropdown, *args):
        idx = dropdown.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION: return
        item = dropdown.get_model().get_string(idx)
        self.current_genre = item
        self.load_movies()
        
    def on_sort_changed(self, dropdown, *args):
        idx = dropdown.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION: return
        
        if self.current_media_type == "anime":
            sort_map = ["trending", "year", "title"]
        else:
            sort_map = ["trending", "popularity", "last added", "year", "title", "rating"]
            
        if idx < len(sort_map):
            self.current_catalog_id = sort_map[idx]
        self.load_movies()
        
    def on_scroll(self, adj):
        if self.is_fetching: return
        # Trigger load when within 400 pixels of the bottom
        if adj.get_value() > 0 and adj.get_value() >= adj.get_upper() - adj.get_page_size() - 400:
            self.load_movies(page=self.current_page + 1)
            
    def load_movies(self, query=None, page=1):
        if self.is_fetching: return
        
        if query is not None:
            self.current_query = query
            
        self.is_fetching = True
        
        def _do_load():
            if page == 1:
                while child := self.flowbox.get_first_child():
                    self.flowbox.remove(child)
                    
            def fetch():
                if self.current_media_type == "favorites":
                    movies = database.get_favorites() if page == 1 else []
                elif self.current_media_type == "watched":
                    movies = database.get_watched() if page == 1 else []
                else:
                    movies = api.fetch_items(media_type=self.current_media_type, query=self.current_query, genre=self.current_genre, catalog_id=self.current_catalog_id, page=page)
                GLib.idle_add(self.populate_movies, movies, page)
                
            threading.Thread(target=fetch, daemon=True).start()
            return False
            
        # Defer heavy grid clearance/repopulation by 20ms to let GTK draw CSS changes first
        GLib.timeout_add(150, _do_load)
        
    def populate_movies(self, movies, page):
        self.is_fetching = False
        if not movies: return
        
        self.current_page = page
        for movie in movies:
            self.flowbox.append(MovieWidget(movie, self.show_movie_details))
            
        # Eagerly fetch second page to guarantee 100 items initially (except on searches)
        if page == 1 and not self.current_query:
            self.load_movies(page=2)
            return
            
        # Give GTK a moment to render, then check if we need more items to fill the screen
        def check_overflow():
            adj = self.scrolled.get_vadjustment()
            # If upper is less than or slightly larger than page_size, there's no real scrollbar
            if adj.get_upper() <= adj.get_page_size() + 50:
                self.load_movies(page=self.current_page + 1)
        GLib.timeout_add(100, check_overflow)
            
    def on_search_changed(self, entry):
        self.load_movies(query=entry.get_text(), page=1)
        
    def show_movie_details(self, movie):
        details_page = MovieDetailsPage(movie, self.hide_movie_details)
        if self.stack.get_child_by_name("details"):
            self.stack.remove(self.stack.get_child_by_name("details"))
        self.stack.add_named(details_page, "details")
        self.stack.set_visible_child_name("details")

    def hide_movie_details(self):
        player.stop_player() # Stop if they go back
        self.stack.set_visible_child_name("grid")

    def on_close_request(self, *args):
        player.stop_player()
        return False
