import tempfile
import pypdf
import os

try:
    import primp
    requests = primp.Client(impersonate='chrome_130')
except ImportError:
    print("Warning: primp not installed, using requests")
    import requests

NYT_URL_PATH = os.getenv('NYT_URL_PATH', 'http://www.nytimes.com/images/{}/nytfrontpage/{}')

class NytSource:
    def __init__(self, date, only_front=True):
        self.date = date
        self.only_front = only_front

    name_prefix = "New York Times"

    def get_pdf_url(self, y, m, d, name='scan.pdf'):
        return NYT_URL_PATH.format('{}/{:0>2}/{:0>2}'.format(y, m, d), name)

    def get_pdf(self):
        y, m, d = self.date[:4], self.date[4:6], self.date[6:8]

        dir = tempfile.gettempdir()
        writer = pypdf.PdfWriter()
        def _fetch_with(name, domain):
            url = self.get_pdf_url(y, m, d, name=name)
            if domain:
                url = url.replace('www.nytimes.com', domain)
            print("nyt: fetching", url)
            r = requests.get(url)
            if r.status_code//100 != 2:
                print("Error", r.status_code, url)
                return None
            else:
                path = os.path.join(dir, "scan.pdf")
                open(path, "wb").write(r.content)
                with open(path, "rb") as file:
                    reader = pypdf.PdfReader(file)
                    writer.append_pages_from_reader(reader)
                    return True

        if not _fetch_with('scan.pdf', None):
            if not _fetch_with('scannat.pdf', None):
                if not _fetch_with('scan.pdf', 'static01.nyt.com'):
                    if not _fetch_with('scannat.pdf', 'static01.nyt.com'):
                        print("Error: failed to fetch any NYT pdf")
                        return None


        path = os.path.join(dir, "{} {}.pdf".format(self.name_prefix, self.date))
        with open(path, "wb") as output_file:
            writer.write(output_file)

        return path



