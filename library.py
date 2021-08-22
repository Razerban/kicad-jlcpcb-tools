import csv
import locale
import logging
import os
import time
from pathlib import Path

# Hack to avoid wx + pandas error "ValueError: unknown locale: en-GB"
try:
    locale.setlocale(locale.LC_ALL, "en")
except:
    pass
# import pandas, install it if not installed and import afterwards
try:
    import pandas as pd
except ImportError:
    import subprocess
    import sys

    subprocess.check_call(["python", "-m", "pip", "install", "pandas"])
    import pandas as pd

import requests


class JLCPCBLibrary:
    def __init__(self):
        self.create_folders()
        self.csv = os.path.join(self.xlsdir, "jlcpcb_parts.csv")
        self.df = None
        self.loaded = False
        self.logger = logging.getLogger(__name__)

    def create_folders(self):
        """Create output folder if not already exist."""
        path, filename = os.path.split(os.path.abspath(__file__))
        self.xlsdir = os.path.join(path, "jlcpcb")
        Path(self.xlsdir).mkdir(parents=True, exist_ok=True)

    def download(self, progress):
        """Download CSV"""
        self.logger.info("Start downloading library")
        CSV_URL = "https://jlcpcb.com/componentSearch/uploadComponentInfo"
        with open(self.csv, "wb") as csv:
            r = requests.get(CSV_URL, allow_redirects=True, stream=True)
            total_length = r.headers.get("content-length")
            if total_length is None:  # no content length header
                csv.write(r.content)
            else:
                dl = 0
                total_length = int(total_length)
                if progress:
                    progress.SetRange(total_length)
                for data in r.iter_content(chunk_size=4096):
                    dl += len(data)
                    if progress:
                        progress.SetValue(dl)
                    csv.write(data)
        if progress:
            progress.SetValue(0)

    def load(self):
        self.df = pd.read_csv(
            self.csv,
            encoding="iso-8859-1",
            header=0,
            names=[
                "LCSC_Part",
                "First_Category",
                "Second_Category",
                "MFR_Part",
                "Package",
                "Solder_Joint",
                "Manufacturer",
                "Library_Type",
                "Description",
                "Datasheet",
                "Price",
                "Stock",
            ],
            index_col=False
        )
        self.partcount = len(self.df)
        self.logger.info(f"Loaded Library with {self.partcount} parts")
        self.loaded = True

    def get_packages(self):
        return [str(pkg) for pkg in self.df["Package"].unique()]

    def get_manufacturers(self):
        return [str(mfr) for mfr in self.df["Manufacturer"].unique()]

    def search(
        self,
        keyword="",
        basic=True,
        extended=False,
        assert_stock=False,
        packages=[],
        manufacturers=[],
    ):
        if len(keyword) < 3:
            return []
        query = [
            f"(LCSC_Part.str.contains('{keyword}'))",
            f"(First_Category.str.contains('{keyword}'))",
            f"(Second_Category.str.contains('{keyword}'))",
            f"(MFR_Part.str.contains('{keyword}'))",
            f"(Description.str.contains('{keyword}'))",
        ]
        df = self.df
        types = []
        if basic:
            types.append("Basic")
        if extended:
            types.append("Extended")
        df = df[df.Library_Type.isin(types)]
        if assert_stock:
            df = df[df.Stock > 0]
        if packages:
            df = df[df.Package.isin(packages)]
        if manufacturers:
            df = df[df.Manufacturer.isin(manufacturers)]
        query = " | ".join(query)
        result = df[df.eval(query)]
        return result
