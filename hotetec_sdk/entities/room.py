from typing import List

from hotetec_sdk.entities.cancellation_restriction import CancellationRestriction
from hotetec_sdk.entities.room_service import RoomService


class Room:
    def __init__(
            self,
            room_id: str,
            distribution: str,
            max_people: int,
            min_people: int,
            adults_max: int,
            children_max: int,
            base_amount: float,
            iva_amount: float,
            tax_amount: float,
            services: List[RoomService] = list,
            cancellation_restrictions: CancellationRestriction | None = None,
            non_commissionable_amount: float | None = None,
            commissionable_amount: float | None = None,
            fare_code: str | None = None,
            fare_name: str | None = None,
            description: str | None = None,
            commercial_name: str | None = None,
    ):
        self.id = room_id
        self.distribution = distribution
        self.fare_code = fare_code
        self.fare_name = fare_name
        self.max_people = max_people
        self.min_people = min_people
        self.adults_max = adults_max
        self.children_max = children_max
        self.non_commissionable_amount = non_commissionable_amount
        self.commissionable_amount = commissionable_amount
        self.base_amount = base_amount
        self.iva_amount = iva_amount
        self.tax_amount = tax_amount
        self.cancellation_restrictions = cancellation_restrictions
        self.services = services
        self.description = description
        self.commercial_name = commercial_name

    def __str__(self):
        return self.id

    @property
    def total_amount(self):
        return (self.base_amount or 0) + (self.tax_amount or 0)
