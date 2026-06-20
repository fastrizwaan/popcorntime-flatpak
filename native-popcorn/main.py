import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk

from window import NativePopcornWindow

class NativePopcornApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='org.popcorntime.NativePopcorn',
                         flags=Gio.ApplicationFlags.NON_UNIQUE)

    def do_activate(self):
        # Force Dark Mode
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        
        # Load custom CSS
        css_provider = Gtk.CssProvider()
        css_data = b"""
        window { background-color: #17181b; }
        .sidebar { background-color: #111215; }
        .sidebar-item { padding: 12px 24px; border-radius: 0; margin: 0; transition: all 200ms ease; font-weight: bold; color: rgba(255, 255, 255, 0.6); }
        .sidebar-item:hover { color: #ffffff; }
        .sidebar-item.selected { border-left: 4px solid #00e57a; color: #ffffff; background-color: rgba(255,255,255,0.05); }
        
        button.suggested-action { background-color: #00e57a; color: #000; font-weight: bold; border: none; }
        button.suggested-action:hover { background-color: #00ff88; }
        
        .pt-card { background-color: transparent; border-radius: 8px; transition: all 200ms ease; }
        .pt-card:hover { transform: scale(1.05); }
        .pt-card-title { font-weight: bold; font-size: 13px; margin-top: 8px; color: #fff; }
        .pt-card-year { font-size: 11px; color: rgba(255, 255, 255, 0.5); }
        
        .backdrop-overlay { background: linear-gradient(to top, #17181b 10%, rgba(23, 24, 27, 0.5) 100%); }
        """
        css_provider.load_from_data(css_data)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), 
            css_provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        win = self.props.active_window
        if not win:
            win = NativePopcornWindow(application=self)
        win.present()

if __name__ == '__main__':
    app = NativePopcornApp()
    sys.exit(app.run(sys.argv))
