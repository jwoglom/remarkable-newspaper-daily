import requests
import tempfile
import pypdf
import os

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
        merger = pypdf.PdfMerger()
        url = self.get_pdf_url(y, m, d)
        print("nyt: fetching", url)
        r = requests.get(url)
        if r.status_code//100 != 2:
            print("Error", r.status_code, url)
            return None
        else:
            path = os.path.join(dir, "scan.pdf")
            open(path, "wb").write(r.content)
            merger.append(path)


        path = os.path.join(dir, "{} {}.pdf".format(self.name_prefix, self.date))
        merger.write(path)
        merger.close()

        return path



