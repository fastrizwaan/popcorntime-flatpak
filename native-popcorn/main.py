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
        .topbar { background-color: #111215; border-bottom: 1px solid #1a1b1f; padding-top: 6px;padding-bottom: 6px; padding-left: 0px; padding-right: 6px;  }
        .topbar-item { padding-top: 0px; padding-bottom: 6px; padding-left: 18px; padding-right: 18px; border-radius: 0; margin-top: 6px; margin-bottom: 0px; transition: all 200ms ease; font-weight: bold; color: rgba(255, 255, 255, 0.6); background: transparent; border: none; border-bottom: 3px solid transparent; outline: none; box-shadow: none; }
        .topbar-item:hover, .topbar-item:focus, .topbar-item:focus-visible { color: #ffffff; background: transparent; outline: none; box-shadow: none; }
        .topbar-item:active { background: transparent; border-bottom: 3px solid transparent; outline: none; box-shadow: none; }
        .topbar-item.selected { border-bottom: 3px solid #2f79c3; color: #ffffff; }
        
        button.suggested-action { background-color: #25405b; color: #ffffff; font-weight: bold; border: none; }
        button.suggested-action:hover { background-color: #2e5175; }
        
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
