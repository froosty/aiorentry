from dataclasses import dataclass


@dataclass
class Page:
    url: str
    edit_code: str
    text: str
