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

    with open(path, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    patch_movie()
    patch_yts()
    patch_tv()
