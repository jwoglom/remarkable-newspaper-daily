import requests
import tempfile
import pypdf
import os

class WapoSource:
    def __init__(self, date, only_front):
        self.date = date
        self.only_front = only_front
    
    name_prefix = "Washington Post"

    def get_json(self, date):
        r = requests.get("https://www.washingtonpost.com/wp-stat/tablet/v1.1/{date}/tablet_{date}.json".format(date=date))
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
        merger = pypdf.PdfMerger()
        for page in data:
            url = self.get_pdf_url(page)
            print("wapo: fetching", url)
            r = requests.get(url)
            if r.status_code//100 != 2:
                print("Error", r.status_code, url)
                continue
            
            path = os.path.join(dir, page[2])
            open(path, "wb").write(r.content)
            merger.append(path)
        

        path = os.path.join(dir, "{} {}.pdf".format(self.name_prefix, date))
        merger.write(path)
        merger.close()

        return path



