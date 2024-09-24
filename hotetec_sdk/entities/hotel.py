from typing import List, Dict

from hotetec_sdk.entities.room import Room


class Hotel:
    def __init__(self, code: str, name: str, category: str, services: list = list,
                 availability: Dict[str, List[Room]] = dict):
        self.name = name
        self.category = category
        self.services = services
        self.code = code
        self.availability = availability

    def __str__(self):
        return self.name
