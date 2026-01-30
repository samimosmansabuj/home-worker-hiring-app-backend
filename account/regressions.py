import re

class DataRegressionFromPassportImage:
    def __init__(self, raw_data: str):
        self.raw = raw_data.upper()

    def extract_name_from_mrz(self) -> str | None:
        mrz_lines = re.findall(r'P<.*', self.raw)
        if not mrz_lines:
            return None

        mrz = mrz_lines[0]
        mrz = re.sub(r'^P<[A-Z]{3}', '', mrz)

        parts = mrz.split('<<')
        if len(parts) < 2:
            return None

        surname = parts[0].replace('<', ' ').strip()
        given = parts[1].replace('<', ' ').strip()

        return f"{given} {surname}".strip()

    def extract_name_from_labels(self) -> str | None:
        patterns = [
            r'GIVEN NAME[S]?\s*\n*([A-Z ]+)',
            r'GIVER NAME\s*\n*([A-Z ]+)',
            r'PRENOMS?\s*\n*([A-Z ]+)',
            r'প্রদত্ত নাম\s*\n*([A-Z ]+)',

            r'SURNAME\s*\n*([A-Z ]+)',
            r'NOM\s*\n*([A-Z ]+)',
            r'বংশগত নাম\s*\n*([A-Z ]+)',
        ]

        found = []
        for p in patterns:
            m = re.search(p, self.raw)
            if m:
                found.append(m.group(1).strip())

        if not found:
            return None

        return " ".join(found)

    def extract_name_fallback(self) -> str | None:
        mrz_match = re.search(r'<<([A-Z<]{5,})', self.raw)
        if not mrz_match:
            return None

        name = mrz_match.group(1).replace('<', ' ')
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def extract_dob(self) -> str | None:
        dob = re.search(
            r'(\d{2}\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{4})',
            self.raw
        )
        return dob.group(1) if dob else None

    # ---------- MASTER ----------
    def extract(self) -> dict:
        name = (
            self.extract_name_from_mrz()
            or self.extract_name_from_labels()
            or self.extract_name_fallback()
        )
        return {
            "name": name,
            "dob": self.extract_dob()
        }

