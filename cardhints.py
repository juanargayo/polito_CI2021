import numpy as np


class CardHints:

    colors = ['red', 'green', 'blue', 'yellow', 'white']

    # When I start every cell is 0, this means that I have no information about the card in this slot (it could be every number and every color)
    def __init__(self, numSlots):   #remove numSlots
        self.values = {v:0 for v in range(1,6)}
        self.colors = {c:0 for c in CardHints.colors}

        #self.values = np.full((numSlots), 0, dtype=int)     #[1, 2, 3, 4, 5]
        #self.colors = np.full((numSlots), 0, dtype=int)     #[R, G, B, Y, W]

    # I put to 1 the cards I am sure of such value/color (direct info)
    def directHintValue(self, val):
        self.values[:]   = -1       #assert the number of ones cannot be more than 1, if not throw exception
        self.values[val] = 1

    def directHintColor(self, val):
        self.colors[:]   = -1
        self.colors[val] = 1

    # I put to -1 the cards I am sure they are not such value/color (indirect info)
    def undirectHintValue(self, val):
        self.values[val] = -1

    def undirectHintColor(self, val):
        self.colors[val] = -1
