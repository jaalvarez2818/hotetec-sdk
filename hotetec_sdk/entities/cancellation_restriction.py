from datetime import datetime


class CancellationRestriction:
    def __init__(self, date: datetime.date = None, percent: float | None = None, amount: float | None = None,
                 text: str | None = None):
        self.date = date
        self.percent = percent
        self.amount = amount
        self.text = text

    def __str__(self):
        return self.date
