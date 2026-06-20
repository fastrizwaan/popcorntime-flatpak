import sys
import threading
import gi

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
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        back_btn = Gtk.Button(icon_name="go-previous-symbolic")
        back_btn.connect("clicked", lambda x: on_back())
        header.pack_start(back_btn)
        header.add_css_class("flat")
        self.main_box.append(header)
        
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
        player.stop_player()
        self.inner_stack.set_visible_child_name("details")
        self.watch_btn.set_sensitive(True)
        self.progress_label.set_text("")
        
    def load_details_async(self):
        def fetch():
            details = api.fetch_movie_details(self.movie_stub.get("id"), self.media_type)
            torrents = []
            if self.media_type != "series":
                torrents = api.get_torrents(self.movie_stub.get("id"), self.media_type)
            GLib.idle_add(self.build_ui, details, torrents)
        threading.Thread(target=fetch, daemon=True).start()
        
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
        
        self.actions_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.actions_hbox.set_margin_top(16)
        
        self.watch_btn = Gtk.Button(label="WATCH IT NOW")
        self.watch_btn.set_css_classes(['suggested-action', 'pill'])
        self.watch_btn.set_size_request(150, 40)
        self.watch_btn.connect("clicked", self.on_watch_clicked)
        self.actions_hbox.append(self.watch_btn)
        
        self.quality_dropdown = Gtk.DropDown.new_from_strings([])
        self.quality_dropdown.set_valign(Gtk.Align.CENTER)
        
        if self.media_type == "series" and details.get("videos"):
            videos = details.get("videos")
            seasons = sorted(list(set([v.get("season") for v in videos if v.get("season")])))
            
            self.season_dropdown = Gtk.DropDown.new_from_strings([f"Season {s}" for s in seasons])
            self.season_dropdown.set_valign(Gtk.Align.CENTER)
            self.actions_hbox.append(self.season_dropdown)
            
            self.episode_dropdown = Gtk.DropDown.new_from_strings([])
            self.episode_dropdown.set_valign(Gtk.Align.CENTER)
            self.actions_hbox.append(self.episode_dropdown)
            
            def on_season_changed(dropdown, *args):
                idx = dropdown.get_selected()
                if idx == Gtk.INVALID_LIST_POSITION: return
                s = seasons[idx]
                self.selected_season = s
                eps = [v for v in videos if v.get("season") == s]
                eps.sort(key=lambda x: x.get("episode", 0))
                self.current_episodes = eps
                ep_strings = [f"Ep {e.get('episode')}: {e.get('title','')}" for e in eps]
                self.episode_dropdown.set_model(Gtk.StringList.new(ep_strings))
                self.episode_dropdown.set_selected(0)
                
            self.season_dropdown.connect("notify::selected", on_season_changed)
            
            def on_episode_changed(dropdown, *args):
                idx = dropdown.get_selected()
                if idx == Gtk.INVALID_LIST_POSITION: return
                self.selected_episode = self.current_episodes[idx].get("episode")
                self.fetch_torrents_async()
                
            self.episode_dropdown.connect("notify::selected", on_episode_changed)
            if seasons: on_season_changed(self.season_dropdown)
        
        self.actions_hbox.append(self.quality_dropdown)
        
        trailer_btn = Gtk.Button()
        trailer_icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
        trailer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        trailer_box.append(trailer_icon)
        trailer_box.append(Gtk.Label(label="Trailer"))
        trailer_btn.set_child(trailer_box)
        trailer_btn.set_valign(Gtk.Align.CENTER)
        trailer_btn.connect("clicked", lambda x: player.play_trailer(details.get("trailer")))
        if not details.get("trailer"): trailer_btn.set_sensitive(False)
        self.actions_hbox.append(trailer_btn)
        
        heart_btn = Gtk.Button(icon_name="emblem-favorite-symbolic")
        heart_btn.set_valign(Gtk.Align.CENTER)
        heart_btn.set_css_classes(['circular'])
        self.actions_hbox.append(heart_btn)
        
        info_vbox.append(self.actions_hbox)
        info_vbox.append(self.progress_label)
        
        top_hbox.append(info_vbox)
        self.content_box.append(top_hbox)
        
        if self.media_type != "series":
            self.torrents = torrents
            self.update_quality_dropdown()
            
    def fetch_torrents_async(self):
        self.watch_btn.set_sensitive(False)
        self.progress_label.set_text("Loading streams...")
        self.quality_dropdown.set_model(Gtk.StringList.new(["Loading..."]))
        def fetch():
            torrents = api.get_torrents(self.movie_stub.get("id"), self.media_type, self.selected_season, self.selected_episode)
            GLib.idle_add(self.on_torrents_fetched, torrents)
        threading.Thread(target=fetch, daemon=True).start()
        
    def on_torrents_fetched(self, torrents):
        self.progress_label.set_text("")
        self.torrents = torrents
        self.update_quality_dropdown()
        
    def update_quality_dropdown(self):
        if not self.torrents:
            self.watch_btn.set_sensitive(False)
            self.quality_dropdown.set_model(Gtk.StringList.new(["No streams"]))
            return
            
        self.watch_btn.set_sensitive(True)
        qualities = [f"{t.get('quality', 'Unknown')} - {t.get('size', '')} (\U0001f464 {t.get('seeders', 0)} seeds)" for t in self.torrents]
        self.quality_dropdown.set_model(Gtk.StringList.new(qualities))
        self.quality_dropdown.set_selected(0)
        
    def on_watch_clicked(self, btn):
        if not self.torrents:
            self.progress_label.set_text("No streams available.")
            return
            
        index = self.quality_dropdown.get_selected()
        if index == Gtk.INVALID_LIST_POSITION:
            index = 0
            
        if index < 0 or index >= len(self.torrents): return
        
        torrent = self.torrents[index]
        magnet = api.build_magnet(torrent.get("hash"), self.movie_stub.get("title", ""))
        
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

class MovieWidget(Gtk.Box):
    def __init__(self, movie, on_card_clicked):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.movie = movie
        
        # Match WineCharm icon view logic but make them slightly larger to fit ~15 per row
        self.set_size_request(130, 195)
        self.set_hexpand(True)
        self.set_halign(Gtk.Align.FILL)
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
        title_label.set_wrap(True)
        title_label.set_lines(1)
        import gi
        gi.require_version('Pango', '1.0')
        from gi.repository import Pango
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.set_max_width_chars(1) # Force minimum width request so grid can pack tight
        title_label.set_halign(Gtk.Align.START)
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

        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_content(main_box)
        
        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_css_classes(['sidebar'])
        sidebar.set_size_request(200, -1)
        
        logo_label = Gtk.Label(label="Popcorn Time")
        logo_label.set_css_classes(['title-2'])
        logo_label.set_margin_top(24)
        logo_label.set_margin_bottom(24)
        sidebar.append(logo_label)
        
        self.movies_btn = Gtk.Button(label="Movies")
        self.movies_btn.set_css_classes(['sidebar-item', 'selected'])
        self.movies_btn.connect("clicked", lambda x: self.switch_category("movie", "All", self.movies_btn))
        sidebar.append(self.movies_btn)
        
        self.tv_btn = Gtk.Button(label="TV Shows")
        self.tv_btn.set_css_classes(['sidebar-item'])
        self.tv_btn.connect("clicked", lambda x: self.switch_category("series", "All", self.tv_btn))
        sidebar.append(self.tv_btn)
        
        self.anime_btn = Gtk.Button(label="Anime")
        self.anime_btn.set_css_classes(['sidebar-item'])
        self.anime_btn.connect("clicked", lambda x: self.switch_category("series", "Animation", self.anime_btn))
        sidebar.append(self.anime_btn)
        
        main_box.append(sidebar)
        
        # Right Content Area (Stack)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_hexpand(True)
        main_box.append(self.stack)
        
        # Grid Page
        self.grid_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        self.grid_page.append(header)
        
        # Header controls
        header_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        genres = [
            "All", "Action", "Adventure", "Animation", "Biography", "Comedy", 
            "Crime", "Documentary", "Drama", "Family", "Fantasy", "History", 
            "Horror", "Music", "Musical", "Mystery", "Romance", "Sci-Fi", 
            "Sport", "Thriller", "War", "Western"
        ]
        self.genre_dropdown = Gtk.DropDown.new_from_strings(genres)
        self.genre_dropdown.set_valign(Gtk.Align.CENTER)
        self.genre_dropdown.connect("notify::selected", self.on_genre_changed)
        header_controls.append(self.genre_dropdown)
        
        self.sort_dropdown = Gtk.DropDown.new_from_strings(["Trending", "Popularity", "Last Added", "Year", "Title", "Rating"])
        self.sort_dropdown.set_valign(Gtk.Align.CENTER)
        self.sort_dropdown.connect("notify::selected", self.on_sort_changed)
        header_controls.append(self.sort_dropdown)
        
        header.pack_start(header_controls)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        header.pack_end(self.search_entry)
        
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
        btn.add_css_class("selected")
        
        self.current_media_type = media_type
        self.current_genre = genre
        self.current_catalog_id = "trending"
        self.sort_dropdown.set_selected(0)
        
        # Reset genre dropdown
        if genre == "Animation":
            self.genre_dropdown.set_selected(2) # Animation index
        else:
            self.genre_dropdown.set_selected(0) # All
            
        self.load_movies()
        
    def on_genre_changed(self, dropdown, *args):
        idx = dropdown.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION: return
        item = dropdown.get_model().get_string(idx)
        self.current_genre = item
        self.load_movies()
        
    def on_sort_changed(self, dropdown, *args):
        idx = dropdown.get_selected()
        sort_map = ["trending", "popularity", "last added", "year", "title", "rating"]
        if idx != Gtk.INVALID_LIST_POSITION:
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
        
        if page == 1:
            while child := self.flowbox.get_first_child():
                self.flowbox.remove(child)
                
        def fetch():
            movies = api.fetch_items(media_type=self.current_media_type, query=self.current_query, genre=self.current_genre, catalog_id=self.current_catalog_id, page=page)
            GLib.idle_add(self.populate_movies, movies, page)
            
        threading.Thread(target=fetch, daemon=True).start()
        
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
