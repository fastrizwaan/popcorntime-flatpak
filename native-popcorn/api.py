import json
import urllib.request
import urllib.parse
import os
import time
import hashlib

cache_dir_base = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
CACHE_DIR = os.path.join(cache_dir_base, 'native-popcorn', 'api')
os.makedirs(CACHE_DIR, exist_ok=True)

def _get_cached_request(url, max_age_hours=12):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_file = os.path.join(CACHE_DIR, url_hash)
    
    # Check if cache exists and is fresh
    if os.path.exists(cache_file):
        age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600
        if age_hours < max_age_hours:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass # Fall back to fetching if cache is corrupted
                
    # Fetch from network
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data_str = response.read().decode('utf-8')
            data = json.loads(data_str)
            # Save to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(data_str)
            return data
    except Exception as e:
        print(f"Error fetching items from {url}: {e}")
        # Return stale cache if network fails
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
    return None

def fetch_items(media_type="movie", query="", genre="", catalog_id="trending", limit=50, page=1):
    if catalog_id in ["trending", "popularity", "rating", "last added"] and media_type == "anime":
        if catalog_id == "popularity":
            cid = "kitsu-anime-popular"
        elif catalog_id == "last added":
            cid = "kitsu-anime-new"
        else:
            cid = "kitsu-anime-trending"
        base_url = f"https://anime-kitsu.strem.fun/catalog/anime/{cid}"
    elif catalog_id in ["trending", "popularity", "rating"]:
        cid = "imdbRating" if catalog_id == "rating" else "top"
        base_url = f"https://v3-cinemeta.strem.io/catalog/{media_type}/{cid}"
    else:
        # Fallback to Popcorn API (fusme.link) for Year, Title, Last Added
        if media_type == "anime":
            endpoint = "shows"
            extra_anime = "&anime=1"
        else:
            endpoint = "movies" if media_type == "movie" else "shows"
            extra_anime = ""
        url = f"https://fusme.link/{endpoint}/{page}?sort={urllib.parse.quote(catalog_id)}&order=-1{extra_anime}"
        if genre and genre != "All":
            url += f"&genre={urllib.parse.quote(genre.lower())}"
        if query:
            url += f"&keywords={urllib.parse.quote(query)}"
            
        data = _get_cached_request(url, max_age_hours=12)
        if not data: return []
        
        items = data if isinstance(data, list) else data.get("results", [])
        movies = []
        for m in items:
            imdb_id = m.get("imdb_id") or m.get("imdb") or m.get("id")
            images = m.get("images", {})
            poster = images.get("poster") or images.get("fanart") or ""
            movies.append({
                "id": imdb_id,
                "title": m.get("title"),
                "year": m.get("year", ""),
                "medium_cover_image": poster,
                "type": media_type
            })
        return movies
        
    skip = (page - 1) * limit
    skip_str = f"skip={skip}" if skip > 0 else ""
    
    if query:
        if page > 1: return []
        extra = f"search={urllib.parse.quote(query)}"
        url = f"{base_url}/{extra}.json"
    elif genre and genre != "All":
        extra = f"genre={urllib.parse.quote(genre)}"
        if skip_str: extra += f"&{skip_str}"
        url = f"{base_url}/{extra}.json"
    else:
        url = f"{base_url}/{skip_str}.json" if skip_str else f"{base_url}.json"
        
    data = _get_cached_request(url, max_age_hours=12)
    if not data:
        return []
        
    metas = data.get("metas", [])
    movies = []
    for m in metas:
        movies.append({
            "id": m.get("id"),
            "title": m.get("name"),
            "year": m.get("releaseInfo", m.get("year", "")),
            "medium_cover_image": m.get("poster"),
            "type": media_type
        })
    return movies

def fetch_movie_details(imdb_id, media_type="movie"):
    if media_type == "anime" and str(imdb_id).startswith("kitsu:"):
        url = f"https://anime-kitsu.strem.fun/meta/anime/{imdb_id}.json"
    else:
        actual_media = "series" if media_type == "anime" else media_type
        url = f"https://v3-cinemeta.strem.io/meta/{actual_media}/{imdb_id}.json"
    data = _get_cached_request(url, max_age_hours=168) # 7 days
    if not data:
        return {}
    meta = data.get("meta", {})
    trailer_id = meta.get("trailer")
    if not trailer_id and meta.get("trailers"):
        trailer_id = meta.get("trailers")[0].get("source")
    if not trailer_id and meta.get("trailerStreams"):
        trailer_id = meta.get("trailerStreams")[0].get("ytId")
        
    return {
        "id": meta.get("id"),
        "title": meta.get("name"),
        "year": meta.get("releaseInfo", meta.get("year", "")),
        "medium_cover_image": meta.get("poster"),
        "background": meta.get("background"),
        "description": meta.get("description", "No synopsis available."),
        "runtime": meta.get("runtime", ""),
        "genre": ", ".join(meta.get("genre", [])),
        "imdbRating": meta.get("imdbRating", ""),
        "trailer": trailer_id,
        "videos": meta.get("videos", [])
    }

def get_torrents(imdb_id, media_type="movie", season=None, episode=None):
    if not imdb_id:
        return []
        
    if media_type == "anime" and str(imdb_id).startswith("kitsu:"):
        if episode is not None:
            url = f"https://torrentio.strem.fun/stream/anime/{imdb_id}:{episode}.json"
        else:
            url = f"https://torrentio.strem.fun/stream/anime/{imdb_id}.json"
    else:
        actual_media = "series" if media_type == "anime" else media_type
        if actual_media == "series" and season is not None and episode is not None:
            url = f"https://torrentio.strem.fun/stream/series/{imdb_id}:{season}:{episode}.json"
        else:
            url = f"https://torrentio.strem.fun/stream/movie/{imdb_id}.json"
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            streams = data.get("streams", [])
            if not streams:
                return []
                
            import re
            valid_streams = []
            for s in streams:
                if not s.get("infoHash"):
                    continue
                    
                title_str = s.get("title", "")
                name_and_title = (s.get("name", "") + " " + title_str)
                
                quality = "Unknown"
                q_val = 0
                if "2160p" in name_and_title.lower() or "4k" in name_and_title.lower(): 
                    quality = "4K"
                    q_val = 4
                elif "1080p" in name_and_title.lower(): 
                    quality = "1080p"
                    q_val = 3
                elif "720p" in name_and_title.lower(): 
                    quality = "720p"
                    q_val = 2
                
                size = ""
                size_match = re.search(r'([\d.]+)\s*(GB|MB)', title_str, re.IGNORECASE)
                if size_match:
                    size = f"{size_match.group(1)} {size_match.group(2).upper()}"
                    
                seeders = 0
                seed_match = re.search(r'👤\s*(\d+)', title_str)
                if seed_match:
                    try:
                        seeders = int(seed_match.group(1))
                    except ValueError:
                        pass
                    
                valid_streams.append({
                    "hash": s["infoHash"],
                    "quality": quality,
                    "q_val": q_val,
                    "size": size,
                    "seeders": seeders,
                    "title": s.get("name", ""),
                    "file_index": s.get("fileIdx")
                })
            
            valid_streams.sort(key=lambda x: (x["q_val"], x["seeders"]), reverse=True)
            return valid_streams
    except Exception as e:
        print(f"Error fetching torrents: {e}")
        
    return []

def build_magnet(hash_string, title):
    encoded_title = urllib.parse.quote(title)
    trackers = [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://tracker.openbittorrent.com:80/announce",
        "udp://tracker.torrent.eu.org:451/announce",
        "udp://exodus.desync.com:6969/announce",
        "udp://explodie.org:6969/announce",
        "udp://p4p.arenabg.com:1337/announce",
        "udp://tracker.leechers-paradise.org:6969/announce",
        "udp://tracker.internetwarriors.net:1337/announce",
        "http://tracker.openbittorrent.com:80/announce",
        "https://tracker.tamersunion.org:443/announce"
    ]
    tracker_str = "&tr=".join([urllib.parse.quote(t) for t in trackers])
    return f"magnet:?xt=urn:btih:{hash_string}&dn={encoded_title}&tr={tracker_str}"
