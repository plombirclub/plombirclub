import json
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

BASE = "http://nginx:80/api"


def request(method, path, data=None, headers=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, resp.read().decode()


def main() -> None:
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def call(method, path, data=None):
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(
            BASE + path,
            data=body,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        with opener.open(req, timeout=20) as resp:
            return resp.status, resp.read().decode()

    call("POST", "/auth/login", {"email": "admin@plombirclub.ru", "password": "Admin123!"})
    for path in [
        "/products/?include_inactive=true&limit=50&page=1",
        "/products?include_inactive=true&limit=50&page=1",
        "/products?page=1&limit=24",
    ]:
        status, payload = call("GET", path)
        data = json.loads(payload)
        items = (data.get("data") or {}).get("items") or []
        print(path, status, "items", len(items), "success", data.get("success"))


if __name__ == "__main__":
    main()
