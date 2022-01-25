import numpy as np


class CardHints:
    # When I start every cell is True, this means that the card in this slot could be every number and every color
    def __init__(self, numSlots):
        self.values = np.full((numSlots), True, dtype=bool)
        self.colors = np.full((numSlots), True, dtype=bool)

    # I put everything to False except the cell that corresponds to that val
    def directHintValue(self, val):
        self.values[:] = False
        self.values[val-1] = True

    def directHintColor(self, val):
        self.colors[:] = False
        self.colors[val-1] = True

    def undirectHintValue(self, val):
        self.values[val-1] = False

    def undirectHintColor(self, val):
        self.colors[val-1] = False
