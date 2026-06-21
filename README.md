## Install

manually via CLI (copy and paste in a terminal):

```bash
flatpak --user remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak --user install flathub org.gnome.Platform//50 org.electronjs.Electron2.BaseApp//25.08
wget -c https://github.com/fastrizwaan/popcorntime-flatpak/releases/download/0.51/org.popcorntime.PopcornTime.flatpak
flatpak install --user org.popcorntime.PopcornTime.flatpak
```

## Build from Source

1 - Install [Flatpak](https://flatpak.org/setup/) & flatpak-builder

2 - Add Flathub remote

```
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

3 - Install required SDKs and BaseApp

```
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50 org.electronjs.Electron2.BaseApp//25.08
```

4 - Clone the repository

```
git clone https://github.com/fastrizwaan/popcorntime-flatpak.git
cd ./popcorntime-flatpak
``` 


5 - Put Popcorn-Time in a local flatpak repository
```
flatpak-builder --user --repo=repo --install-deps-from=flathub --force-clean build-dir org.popcorntime.PopcornTime.json
```

6 - Install Popcorn-Time
```
flatpak --user remote-add --no-gpg-verify popcorn-time-repo repo
flatpak --user install popcorn-time-repo org.popcorntime.PopcornTime
```

7 - Create flatpak-bundle (.flatpak file)
```
flatpak build-bundle ~/.local/share/flatpak/repo org.popcorntime.PopcornTime.flatpak org.popcorntime.PopcornTime
```


cloned from https://gitlab.com/Preisschild/popcorntime-flatpak
