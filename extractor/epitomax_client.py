import requests

class EpitomaxSession:
    def __init__(self):
        self.session = requests.Session()
        self.authenticated = False

    def authenticate(self, username, password):
        url = f"https://my.epitomax.net/epitomax/logout.jsp?j_username={username}&j_password={password}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        resp = self.session.get(url, headers=headers, allow_redirects=True)
        print("Status:", resp.status_code)
        print("Final URL:", resp.url)
        print("Redirect history:", [r.url for r in resp.history])
        print("Cookies after auth:", self.session.cookies)
        print("Response (first 500 chars):", resp.text[:500])
        self.authenticated = True  # Assume authenticated for now

    def download_pdf(self, pdf_url):
        if not self.authenticated:
            raise Exception("Not authenticated.")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://my.epitomax.net/epitomax/",
            "Accept": "application/pdf"
        }
        resp = self.session.get(pdf_url, headers=headers, allow_redirects=True)
        print("Download Status:", resp.status_code)
        print("Download Headers:", resp.headers)
        print("Download Cookies:", self.session.cookies)
        print("Download Response (first 500 chars):", resp.text[:500])
        if resp.status_code == 200 and resp.headers.get("Content-Type", "").startswith("application/pdf"):
            return resp.content
        else:
            raise Exception("Failed to download PDF. Check URL or authentication.") 