import urllib.request
def check(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            print(f"OK: {url}")
    except Exception as e:
        print(f"ERR: {url} - {e}")
check("https://v3-cinemeta.strem.io/catalog/series/top.json")
check("https://v3-cinemeta.strem.io/catalog/movie/top/genre=Action.json")
check("https://v3-cinemeta.strem.io/catalog/series/top/genre=Animation.json")
