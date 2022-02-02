import numpy as np


class CardHints:

    colors = ['red', 'yellow', 'green', 'blue', 'white']

    # When I start every cell is 0, this means that I have no information about the card in this slot (it could be every number and every color)
    def __init__(self, numSlots):   #remove numSlots
        self.values = {v:0 for v in range(1,6)}
        self.colors = {c:0 for c in CardHints.colors}
        self.age    = 0

        #self.values = np.full((numSlots), 0, dtype=int)     #[1, 2, 3, 4, 5]
        #self.colors = np.full((numSlots), 0, dtype=int)     #[R, G, B, Y, W]

    # I put to 1 the cards I am sure of such value/color (direct info)
    def directHintValue(self, val):
        for v in self.values.keys():
            self.values[v]   = -1   if self.values[v] != 1 else self.values[v]    #assert the number of ones cannot be more than 1, if not throw exception
        self.values[val] = 1
        
        occurrences = list(self.values.values()).count(1)
        try:
            assert occurrences <= 1
        except AssertionError:
            print(f"AssertionError: there are {occurrences} occurrences of number 1")

    def directHintColor(self, val):
        for c in self.colors.keys():
            self.colors[c]  = -1    if self.colors[c] != 1 else self.colors[c]
        self.colors[val] = 1

        occurrences = list(self.colors.values()).count(1)
        try:
            assert occurrences <= 1
        except AssertionError:
            print(f"AssertionError: there are {occurrences} occurrences of number 1")

    # I put to -1 the cards I am sure they are not such value/color (indirect info)
    def undirectHintValue(self, val):
        self.values[val] = -1

    def undirectHintColor(self, val):
        self.colors[val] = -1

    def incrementAge(self):
        self.age +=1
