import os

def patch_movie():
    path = '/app/popcorntime/src/app/butter-provider/movie.js'
    with open(path, 'r') as f:
        content = f.read()
    
    # Patch detail
    old_detail = """  detail(imdb_id, old_data, debug) {
    return new Promise((resolve, reject) => resolve(old_data));
  }"""
    new_detail = """  async detail(imdb_id, old_data, debug) {
    try {
      const torrentio = await require('./torrentio')('movie', imdb_id);
      if (torrentio.length > 0) {
        old_data.torrents = old_data.torrents || {};
        torrentio.forEach(t => {
          old_data.torrents[t.quality] = t;
        });
      }
    } catch (e) { console.error('Torrentio error in detail:', e); }
    return old_data;
  }"""
    content = content.replace(old_detail, new_detail)

    # Patch torrents
    old_torrents = """  torrents(imdb_id, lang) {
    const params = {
      locale: this.language,
      contentLocale: lang,
    };
    const uri = `movie/${imdb_id}/torrents?` + new URLSearchParams(params);
    return this._get(0, uri);
  }"""
    new_torrents = """  torrents(imdb_id, lang) {
    const params = {
      locale: this.language,
      contentLocale: lang,
    };
    const uri = `movie/${imdb_id}/torrents?` + new URLSearchParams(params);
    return this._get(0, uri).then(async (pts) => {
      let torrentio = [];
      try {
        torrentio = await require('./torrentio')('movie', imdb_id);
      } catch (e) {}
      return (pts || []).concat(torrentio);
    }).catch(async (e) => {
      let torrentio = [];
      try {
        torrentio = await require('./torrentio')('movie', imdb_id);
      } catch (err) {}
      return torrentio;
    });
  }"""
    content = content.replace(old_torrents, new_torrents)

    with open(path, 'w') as f:
        f.write(content)

def patch_yts():
    path = '/app/popcorntime/src/app/butter-provider/yts.js'
    with open(path, 'r') as f:
        content = f.read()

    # Patch detail
    old_detail = """  detail(torrent_id, old_data, debug) {
    return new Promise((resolve, reject) => resolve(old_data));
  }"""
    new_detail = """  async detail(torrent_id, old_data, debug) {
    try {
      const imdb_id = old_data.imdb_id || torrent_id;
      const torrentio = await require('./torrentio')('movie', imdb_id);
      if (torrentio.length > 0) {
        old_data.torrents = old_data.torrents || {};
        torrentio.forEach(t => {
          old_data.torrents[t.quality] = t;
        });
      }
    } catch (e) { console.error('Torrentio error in detail:', e); }
    return old_data;
  }"""
    content = content.replace(old_detail, new_detail)

    # Patch torrents
    old_torrents = """  torrents(imdb_id, lang, altShowAll) {
    const params = {
      locale: this.language,
      contentLocale: lang,
    };
    const uri = `movie/${imdb_id}/torrents?` + new URLSearchParams(params);
    return this._get(0, uri, altShowAll);
  }"""
    new_torrents = """  torrents(imdb_id, lang, altShowAll) {
    const params = {
      locale: this.language,
      contentLocale: lang,
    };
    const uri = `movie/${imdb_id}/torrents?` + new URLSearchParams(params);
    return this._get(0, uri, altShowAll).then(async (pts) => {
      let torrentio = [];
      try {
        torrentio = await require('./torrentio')('movie', imdb_id);
      } catch (e) {}
      return (pts || []).concat(torrentio);
    }).catch(async (e) => {
      let torrentio = [];
      try {
        torrentio = await require('./torrentio')('movie', imdb_id);
      } catch (err) {}
      return torrentio;
    });
  }"""
    content = content.replace(old_torrents, new_torrents)

    with open(path, 'w') as f:
        f.write(content)

def patch_tv():
    path = '/app/popcorntime/src/app/butter-provider/tv.js'
    with open(path, 'r') as f:
        content = f.read()

    old_torrents = """  episodeTorrents(imdb_id, lang, season, episode) {
    const params = {
      locale: this.language,
      contentLocale: lang,
    };
    const uri = `show/${imdb_id}/${season}/${episode}/torrents?` + new URLSearchParams(params);
    return this._get(0, uri);
  }"""
    new_torrents = """  episodeTorrents(imdb_id, lang, season, episode) {
    const params = {
      locale: this.language,
      contentLocale: lang,
    };
    const uri = `show/${imdb_id}/${season}/${episode}/torrents?` + new URLSearchParams(params);
    return this._get(0, uri).then(async (pts) => {
      let torrentio = [];
      try {
        torrentio = await require('./torrentio')('series', imdb_id, season, episode);
      } catch (e) {}
      return (pts || []).concat(torrentio);
    }).catch(async (e) => {
      let torrentio = [];
      try {
        torrentio = await require('./torrentio')('series', imdb_id, season, episode);
      } catch (err) {}
      return torrentio;
    });
  }"""
    content = content.replace(old_torrents, new_torrents)

    old_content_on_lang = """  contentOnLang(imdb_id, lang, title1) {
    const params = {};
    if (this.language) {
      params.locale = this.language;
    }
    if (this.language !== lang) {
      params.contentLocale = lang;
    }
    const uri = `show/${imdb_id}?` + new URLSearchParams(params);

    return this._get(0, uri).then(data => {
      if (title1) {
        data.title = title1;
      }
      return data;
      return sanitize(data);
    });
  }"""
    
    new_content_on_lang = """  contentOnLang(imdb_id, lang, title1) {
    const params = {};
    if (this.language) {
      params.locale = this.language;
    }
    if (this.language !== lang) {
      params.contentLocale = lang;
    }
    const uri = `show/${imdb_id}?` + new URLSearchParams(params);

    return this._get(0, uri).then(async data => {
      if (title1) {
        data.title = title1;
      }
      
      try {
        const fetchFunc = typeof window !== 'undefined' && window.fetch ? window.fetch : fetch;
        const traktRes = await fetchFunc(`https://api.trakt.tv/shows/${imdb_id}/seasons?extended=episodes`, {
            headers: {
                'trakt-api-version': '2',
                'trakt-api-key': '647c69e4ed1ad13393bf6edd9d8f9fb6fe9faf405b44320a6b71ab960b4540a2'
            }
        });
        if (traktRes.ok) {
            const traktSeasons = await traktRes.json();
            const existingEps = {};
            (data.episodes || []).forEach(e => {
                existingEps[`${e.season}-${e.episode}`] = true;
            });
            
            data.episodes = data.episodes || [];
            
            traktSeasons.forEach(season => {
                if (season.number === 0) return;
                
                if (season.episodes) {
                    season.episodes.forEach(ep => {
                        if (!existingEps[`${ep.season}-${ep.number}`]) {
                            data.episodes.push({
                                season: ep.season,
                                episode: ep.number,
                                title: ep.title,
                                overview: ep.overview,
                                first_aired: ep.first_aired ? new Date(ep.first_aired).getTime() / 1000 : 0,
                                tvdb_id: ep.ids.tvdb,
                                torrents: {}
                            });
                        }
                    });
                }
            });
        }
      } catch (err) {
        console.error('Error fetching full episodes from Trakt', err);
      }
      
      return data;
    });
  }"""
    content = content.replace(old_content_on_lang, new_content_on_lang)

    with open(path, 'w') as f:
        f.write(content)

def patch_show_detail():
    path = '/app/popcorntime/src/app/lib/views/show_detail.js'
    with open(path, 'r') as f:
        content = f.read()

    # Patch selectTorrent to handle undefined torrent
    old_select = """        selectTorrent: function(torrent, key) {
            var startStreaming = $('.startStreaming');
            var downloadButton = $('#download-torrent');
            startStreaming.attr('data-file', torrent.file || '');
            startStreaming.attr('data-torrent', torrent.url);
            startStreaming.attr('data-source', torrent.source);
            startStreaming.attr('data-provider', torrent.provider);
            startStreaming.attr('data-quality', key);
            downloadButton.attr('data-torrent', torrent.url);
            downloadButton.attr('data-file', torrent.file || '');"""
    
    new_select = """        selectTorrent: function(torrent, key) {
            var startStreaming = $('.startStreaming');
            var downloadButton = $('#download-torrent');
            if (!torrent) {
                startStreaming.addClass('disabled').css('pointer-events', 'none');
                downloadButton.addClass('disabled').css('pointer-events', 'none');
                return;
            }
            startStreaming.removeClass('disabled').css('pointer-events', 'auto');
            downloadButton.removeClass('disabled').css('pointer-events', 'auto');
            startStreaming.attr('data-file', torrent.file || '');
            startStreaming.attr('data-torrent', torrent.url);
            startStreaming.attr('data-source', torrent.source);
            startStreaming.attr('data-provider', torrent.provider);
            startStreaming.attr('data-quality', key);
            downloadButton.attr('data-torrent', torrent.url);
            downloadButton.attr('data-file', torrent.file || '');"""
    
    content = content.replace(old_select, new_select)

    # Patch onUpdateTorrentsList to inject Torrentio streams into qualitySelector
    old_update = """            this.getRegion('torrentList').empty();
            const torrentList = new App.View.TorrentList({
                model: new Backbone.Model({
                    provider: showProvider,
                    promise: showProvider.episodeTorrents(this.model.get('imdb_id'), info.locale, episode.season, episode.episode),
                }),
            });
            this.getRegion('torrentList').show(torrentList);"""

    new_update = """            this.getRegion('torrentList').empty();
            var _thisLocal = this;
            const torrentList = new App.View.TorrentList({
                model: new Backbone.Model({
                    provider: showProvider,
                    promise: showProvider.episodeTorrents(this.model.get('imdb_id'), info.locale, episode.season, episode.episode).then(torrents => {
                        if (torrents && torrents.length > 0) {
                            let torrentsDict = {};
                            torrents.forEach(t => {
                                torrentsDict[t.quality] = t;
                            });
                            episode.torrents = Object.assign({}, episode.torrents, torrentsDict);
                            if (_thisLocal.getRegion('qualitySelector').currentView) {
                                _thisLocal.getRegion('qualitySelector').currentView.updateTorrents(episode.torrents);
                            }
                        }
                        return torrents;
                    }),
                }),
            });
            this.getRegion('torrentList').show(torrentList);"""
    
    content = content.replace(old_update, new_update)

    with open(path, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    patch_movie()
    patch_yts()
    patch_tv()
    patch_show_detail()
