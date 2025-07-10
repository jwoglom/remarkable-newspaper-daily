import tempfile
import pypdf
import os
from datetime import datetime

try:
    import primp
    requests = primp.Client(impersonate='chrome_130')
except ImportError:
    print("Warning: primp not installed, using requests")
    import requests

HEADERS = {"User-Agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'}
class WapoSource:
    def __init__(self, date, only_front):
        self.date = date
        self.only_front = only_front

    name_prefix = "Washington Post"

    def get_json(self, date):
        r = requests.get("https://www.washingtonpost.com/wp-stat/tablet/v1.1/{date}/tablet_{date}.json".format(date=date), headers=HEADERS)
        if r:
            return r.json()

    def parse_json(self, jsond, only_front=False):
        data = []

        date = jsond["sections"]["pubdate"]
        sections = jsond["sections"]["section"]
        for section in sections:
            sname = section["name"]
            pages = section["pages"]["page"]
            for page in pages:
                if (only_front and page["page_name"] == 'A01') or not only_front:
                    data.append((date, page["page_name"], page["hires_pdf"], page["thumb_300"]))

        return data

    def get_pdf_url(self, info):
        return "https://www.washingtonpost.com/wp-stat/tablet/v1.1/{date}/{pdf}".format(date=info[0], pdf=info[2])

    def get_pdf(self):
        date = self.date
        jsond = self.get_json(date)
        if not jsond:
            return None

        data = self.parse_json(jsond, only_front=self.only_front)
        print("wapo: got JSON", data)

        dir = tempfile.gettempdir()
        writer = pypdf.PdfWriter()
        for page in data:
            url = self.get_pdf_url(page)
            print("wapo: fetching", url)
            r = requests.get(url, headers=HEADERS)
            if r.status_code//100 != 2:
                print("Error", r.status_code, url)
                return None

            path = os.path.join(dir, page[2])
            open(path, "wb").write(r.content)
            with open(path, "rb") as file:
                reader = pypdf.PdfReader(file)
                writer.append_pages_from_reader(reader)


        path = os.path.join(dir, "{} {}.pdf".format(self.name_prefix, date))
        with open(path, "wb") as output_file:
            writer.write(output_file)

        return path



if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser(description="Download Washington Post pdf")
    a.add_argument('--date', default=datetime.now().strftime("%Y%m%d"), help='override the current day used to fetch newspapers, in YYYYMMDD format')
    a.add_argument('--only-front', action="store_true", help='Only fetch front page')
    args = a.parse_args()

    source = WapoSource(args.date, args.only_front)
    print(source.get_pdf())