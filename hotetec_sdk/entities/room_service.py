class RoomService:
    def __init__(self, name: str, reference: str):
        self.reference = reference
        self.name = name

    def __str__(self):
        return self.name
