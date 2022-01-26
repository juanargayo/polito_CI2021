import numpy as np


class CardHints:
    # When I start every cell is 0, this means that I have no information about the card in this slot (it could be every number and every color)
    def __init__(self, numSlots):
        self.values = np.full((numSlots), 0, dtype=int)
        self.colors = np.full((numSlots), 0, dtype=int)

    # I put to 1 the cards I am sure of such value/color (direct info)
    def directHintValue(self, val):
        self.values[val] = 1

    def directHintColor(self, val):
        self.colors[val] = 1

    # I put to -1 the cards I am sure they are not such value/color (indirect info)
    def undirectHintValue(self, val):
        self.values[val] = -1

    def undirectHintColor(self, val):
        self.colors[val] = -1
