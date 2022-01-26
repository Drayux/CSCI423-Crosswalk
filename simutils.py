# SIMULATION UTILITIES
# Written by: Liam Dempsey
# Version: 0.1.5
# A bunch of the LGA stuff conglomerated into one file!

import math
import os
import random as pyrandom

# ============================================================================ #
#   Useful objects for use in simluations
# ============================================================================ #

# API for file I/O the way Hellman likes (͡° ͜ʖ ͡°)
class Token:
    def __init__(self, tf):
        try: self.trace = open(tf, 'r')  # File object of tracefile
        except (FileNotFoundError, OSError):
            print(f"ERROR: Could not open trace file {tf}")
            self.trace = None
            exit(-1)

        # If tracefile is empty, it likely was not accessed properly
        # if os.path.getsize(tf) == 0:
        #     print(f"ERROR: Trace file {tf} has no data")
        #     exit(-1)

        self.curval = -1            # Last value pulled from the tracefile
        self.count = 0              # Total number of values read from the tracefile
        self.iter = iter(self.iterate())

    # Restore the resources when the object is destroyed
    # ^^The garbage collector seems to act a bit weird, but creating a new Token
    #   on the same file, before the previous Token is destroyed does not seem
    #   to cause any issues. YMMV!
    def __del__(self):
        if self.trace is not None and not self.trace.closed: self.trace.close()

    def __iter__(self):
        return TokenIter(self)

    def __str__(self):
        return str(self.curval)

    def iterate(self):
        for line in self.trace:
            try: yield float(line.strip())
            except ValueError: raise StopIteration  # Empty line, EOF has been reached (assuming proper TF is used)

    # Get the next value in the file (without all the setup work!)
    def next(self):
        try:
            self.curval = next(self.iter)
            self.count += 1
            return self.curval

        except StopIteration:
            print(f"ERROR: Reached end of tracefile! Read {self.count} values")
            return 0.0

# Token iterator object for 'for x in y' syntax. Works the same way as file IO:
# (Where you can only do the full loop once because the iterator is not reset)
class TokenIter:
    def __init__(self, token):
        self._token = token

    def __next__(self):
        # StopIteration will be raised from the next(iter) function so we needn't add the condition
        self._token.curval = next(self._token.iter)
        self._token.count += 1
        return self._token.curval


# API for Welford's one-pass equations
class Welford:
    def __init__(self, name = "Welford"):
        self.name = name
        self.avg = 0.0       # Distribution mean
        self.var = 0.0       # Progressive, needs to be divided by n
        self.i = 0           # Number of elements added to the Welford object

    def __str__(self):
        return f"{self.name}: x̄ = {self.avg}, std = {self.std()}, i = {self.i}"

    def insert(self, x):
        try: x = float(x)
        except ValueError: return

        self.i += 1
        avg = self.avg + ((x - self.avg) / self.i)
        var = self.var + ((self.i - 1) * ((x - self.avg) ** 2) / self.i)

        # Alternative calculation for variance
        # It yields the same result, but I don't know the proof well enough to
        # be able to explain *why* it gives the same result
        #var = self.var + ((x - self.avg) * (x - avg))

        self.avg = avg
        self.var = var

    def mean(self):
        return self.avg

    def variance(self):
        return ((self.var / self.i) if self.i > 0 else 0)

    def std(self):
        return self.variance() ** 0.5


# ============================================================================ #
#   Miscellaneous sample/population utility functions
# ============================================================================ #

# Revised random function that uses accept/reject to exclude u = 0.0
def random():
    x = pyrandom.random()
    while x == 0.0: x = pyrandom.random()
    return x


# The Fisher-Yates shuffling algorithm (shuffles passed array in place)
def shuffle(arr, token = None):
    length = len(arr)
    for index in range(length - 1):
        swap = equilikely(index, length - 1, token)
        hold = arr[swap]
        arr[swap] = arr[index]
        arr[index] = hold


# The reservior sampling algorithm (returns a new array containing the pop sample)
def sample(arr, ssize, token = None):
    # Build the inital sample
    data = []
    for i in range(ssize):
        try: data.append(arr[i])
        except IndexError: return data

    # Start ejecting people off the bus at random
    for i in range(ssize, len(arr)):
        # Get the next value from the sample data
        val = arr[i]

        # If bernouli is a success, randomly place it into the sample array
        if bernouli(ssize / (i + 1)):
            i = equilikely(0, ssize - 1, token)
            data[i] = val

    return data


# ============================================================================ #
#   Basic functions for random variates
#     Depending on the application, sometimes we may want to use the built-in
#     random function, other times we may want to use input from a file.
#     Pass in a Token object to specify the latter.
# ============================================================================ #

# DISCRETE
# Simple TRUE/FALSE with success rate p
def bernouli(p, token = None):
    u = (token.next() if type(token) is Token else random())
    return u >= 1.0 - p

# Pascal random variate
def pascal(n, p):
    raise NotImplementedError("Pascal random variate")

# Binomial random variate
def binomial(n, p):
    raise NotImplementedError("Binomial random variate")

# Equilikely random variate (Integers with equal chance in range [a, b])
def equilikely(a, b, token = None):
    u = (token.next() if type(token) is Token else random())
    return a + int((b - a + 1) * u)

# Geometric random variate (Integers averaging 1/l in range [0, inf))
def geometric(l, token = None):
    if l <= 0.0: raise ValueError("Geometric variate requires l > 0")
    u = (token.next() if type(token) is Token else random())
    return int(math.log(1.0 - u) / math.log(l))

# CONTINUOUS
# Uniform random variate (Floats with equal chance in range [a, b))
def uniform(a, b, token = None):
    u = (token.next() if type(token) is Token else random())
    return a + ((b - a) * u)

# Normal random variate
def normal(mean, stddev):
    raise NotImplementedError("Normal random variate")

# Exponential random variate (Floats averaging l in range (0, inf))
def exponential(l, token = None):
    if l <= 0.0: raise ValueError("Exponential variate requires l > 0")
    u = (token.next() if type(token) is Token else random())
    return -l * math.log(1.0 - u)
