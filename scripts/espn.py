import time
import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "application/json"})

def get_json(url, retries=3, sleep=0.6):
    last = None
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=30)
            if r.status_code == 200:
                time.sleep(sleep)
                return r.json()
            last = f"{r.status_code} {url}"
        except Exception as e:
            last = str(e)
        time.sleep(1.5 * (i + 1))
    print("FAIL", last)
    return None

def get_text(url, retries=3, sleep=0.4):
    last = None
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=30)
            if r.status_code == 200:
                time.sleep(sleep)
                return r.content
            last = f"{r.status_code} {url}"
        except Exception as e:
            last = str(e)
        time.sleep(1.5 * (i + 1))
    print("FAIL", last)
    return None
