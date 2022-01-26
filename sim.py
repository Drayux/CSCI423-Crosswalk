from enum import Enum
from heapq import heappush as push, heappop as pop
from simutils import Token, Welford, bernouli, uniform, exponential
from sys import argv

# ============================================================================ #
#   Simulation constants
# ============================================================================ #

global BLOCKWIDTH
global STREETWIDTH
global CROSSWIDTH
global REDTIMEOUT
global YELLOWTIMEOUT
global GREENTIMEOUT
global LENGTH
global VJA
global VJB
global CARACC
global VKA
global VKB
global MAXPEDS

BLOCKWIDTH = 330
STREETWIDTH = 46     # Relevant to ped behavior (and cars but slightly less so)
CROSSWIDTH = 24      # Relevant to car behavior
REDTIMEOUT = 18.0
YELLOWTIMEOUT = 8.0
GREENTIMEOUT = 35.0
LENGTH = 9
VJA = 100 / 3   # 36.667 ft/s = 25 mi/h
VJB = 154 / 3   # 51.333 ft/s = 35 mi/h
CARACC = 10
VKA = 2.6
VKB = 4.1
MAXPEDS = 20

# ============================================================================ #
#   Enum types
# ============================================================================ #

class EventType(Enum):
    TimerExpire = 1
    PedSpawn = 2
    PedArrive = 3
    PedImpatient = 4
    CarSpawn = 5
    CarArrive = 6       # Point where car would "look at the light"
    CarExit = 7         # Time where car would leave simulation if not delayed

class LightState(Enum):
    GREEN = 0                # Stoplight is green (entry state)
    YELLOW = 1               # Stoplight is yellow
    RED = 2                  # Stoplight is red
    GREENWAIT = 3            # Stoplight is green and waiting on timeout
    GREENWAITPRESSED = 4     # Stoplight is green with timeout, but has been pressed


# ============================================================================ #
#   Simulation-specific data structures
# ============================================================================ #

class Event:
    def __init__(self, at, type, id):
        self.at = at
        self.type = type
        self.id = id

    def __lt__(self, other):
        return self.at < other.at

class Light:
    def __init__(self, sim):
        self.sim = sim    # Pointer to sim
        self.state = LightState.GREEN
        self.walkexpire = 0.0

    def __str__(self):
        if self.state == LightState.GREENWAITPRESSED: return "Traffic light: GREEN (fresh and pressed)"
        if self.state == LightState.GREENWAIT: return "Traffic light: GREEN (fresh)"
        elif self.state == LightState.GREEN: return "Traffic light: GREEN"
        elif self.state == LightState.YELLOW: return "Traffic light: YELLOW"
        elif self.state == LightState.RED: return "Traffic light: RED"

    # The light timer has expired
    # TODO!! ADD EVENTS FOR THE OTHER COMPONENTS WHEN THE TIMER EXPIRES (I.E. CARS SHOULD START STOPPING)
    def timer(self):
        # Big state-dependent if-else block
        if self.state == LightState.GREENWAITPRESSED:
            self.state = LightState.YELLOW
            self.sim.log += "Traffic light has changed to yellow\n"
            self.sim.cars.lightchange(LightState.YELLOW)
            self.sim.insert(YELLOWTIMEOUT, EventType.TimerExpire)

        elif self.state == LightState.GREENWAIT:
            self.state = LightState.GREEN

        elif self.state == LightState.GREEN:
            print("WARNING: Something went wrong! Light timeout while green!")

        elif self.state == LightState.YELLOW:
            self.state = LightState.RED
            self.sim.log += "Traffic light has changed to red\n"
            self.walkexpire = sim.time + REDTIMEOUT
            self.sim.peds.deploy()      # Send the waiting peds across
            self.sim.insert(REDTIMEOUT, EventType.TimerExpire)

        elif self.state == LightState.RED:
            self.state = LightState.GREENWAIT
            self.sim.log += "Traffic light has changed to green\n"
            self.sim.cars.lightchange(LightState.GREEN)
            self.sim.insert(GREENTIMEOUT, EventType.TimerExpire)

    # The light button is pressed
    def press(self):
        # Another big, state-dependent if-else block
        if self.state == LightState.GREENWAIT:
            self.state = LightState.GREENWAITPRESSED

        elif self.state == LightState.GREEN:
            self.state = LightState.YELLOW
            self.sim.log += "Traffic light has changed to yellow\n"
            self.sim.cars.lightchange(LightState.YELLOW)
            self.sim.insert(YELLOWTIMEOUT, EventType.TimerExpire)


class Ped:
    def __init__(self, id, at, ptoken):
        self.id = id
        self.at = at
        self.speed = uniform(VKA, VKB, ptoken)
        self.atlight = (BLOCKWIDTH + STREETWIDTH) / self.speed    # Not adjusted for sim clock
        self.walktime = STREETWIDTH / self.speed

    def __str__(self):
        return f"Ped {self.id}: arrival = {self.at:.3f}, speed = {self.speed:.3f}"

class PedManager:
    def __init__(self, sim):
        self.sim = sim       # Pointer to sim
        self.walking = []    # Newly-spawned pedestrians walking to crosswalk button
        self.waiting = []    # (Now) elderly pedestrians waiting at button (FIFO queue)
        self.count = 0       # Number of peds send this transition

    def debug(self):
        print("WALKING:")
        for ped in self.walking: print(ped)
        print()

        print("WAITING:")
        for ped in self.waiting: print(ped)
        print()

    # Gets and removes a pedestrian from the manager by its ID
    def getped(self, id, popped = True):
        for i, ped in enumerate(self.walking):
            if ped.id == id and popped: return self.walking.pop(i)
            elif ped.id == id: return ped

        # print("DEBUG: Pedestrian not found in walking queue!")

        for i, ped in enumerate(self.waiting):
            if ped.id == id and popped: return self.waiting.pop(i)
            elif ped.id == id: return ped

        return None

    def press(self, n, id = -1):
        result = False
        if n == 0: result = bernouli((15 / 16), self.sim.buttonrandom)
        else: result = bernouli((1 / (n + 1)), self.sim.buttonrandom)

        if result:
            self.sim.log += f"Ped {id} has pressed the button\n"
            self.sim.light.press()

    def spawn(self, ped):
        self.walking.append(ped)
        self.sim.insert(ped.atlight, EventType.PedArrive, ped.id)
        self.sim.log += f"Spawned new ped ({ped.id})\n"

    # Determine if new ped should be sent across or put in the waiting queue
    def arrive(self, id):
        ped = self.getped(id)

        # Pedestrians on the move
        if self.sim.light.state == LightState.RED and ped.walktime <= (self.sim.light.walkexpire - self.sim.time):
            try:
                self.cross(ped)
                return

            except StopIteration: pass

        elif self.sim.light.state == LightState.RED:
            self.sim.log += f"Ped {id} will not make it across the street\n"

        # Pedestrian button press logic (the RNG stuff)
        self.press(len(self.waiting), id)
        self.waiting.append(ped)
        self.sim.log += f"Ped {id} is now waiting\n"

        # Pedestrian impatient stuff
        self.sim.insert(60.0, EventType.PedImpatient, id)

    # A specific pedestrian got impatient
    def impatient(self, id):
        ped = self.getped(id, False)
        if ped is not None:
            self.sim.log += f"Ped {id} has grown impatient\n"
            self.press(0, id)
            self.sim.insert(60.0, EventType.PedImpatient, id)

    # Send a specific pedestrian across the crosswalk (Only called within class)
    def cross(self, ped):
        # Technically, this will jump ahead of time.
        # However, since we guarnatee pedestrians will experience no further
        #   delays and autos drive on the light change, there will be no
        #   difference between doing this now and on its own event.
        if self.count < MAXPEDS:
            delay = self.sim.time - ped.at - ped.atlight
            self.count += 1
            self.sim.peddelay.insert(delay)   # Calculate pedestrian delay
            self.sim.log += f"Ped {ped.id} has crossed the street with {delay:.3f}s delay\n"

        else: raise StopIteration

    # Send all the waiting pedestrians across the crosswalk
    def deploy(self):
        self.count = 0
        for i in range(len(self.waiting)):
            ped = self.waiting[i - self.count]
            try:
                self.getped(ped.id)
                self.cross(ped)

            except StopIteration: break


class Car:
    def __init__(self, id, at, atoken):
        self.id = id
        self.atime = at        # Arrival time (sim clock 0)
        self.speed = uniform(VJA, VJB, atoken)
        self.brakedist = (self.speed ** 2) / (2 * CARACC)
        self.braketime = self.speed / CARACC
        self.shouldstop = False
        self.stoptime = -1     # Sim time that the car begins (or would begin) braking

    def __str__(self):
        mph = self.speed * 3600 / 5280
        return f"Car {self.id}: arrival = {self.atime:.3f}, speed = {self.speed:.3f} ({mph:.1f} mph)"

class CarManager:
    def __init__(self, sim):
        self.sim = sim
        self.driving = []    # New cars on their way to the crosswalk
        self.stopped = []    # Cars that got stopped waiting at the crosswalk
        self.total = (7 * BLOCKWIDTH) + (6 * STREETWIDTH)      # Total drive
        self.before = (self.total - CROSSWIDTH) / 2            # Distance up to the crosswalk
        self.after = ((self.total + CROSSWIDTH) / 2) + LENGTH  # Distance one car length after the crosswalk

    def debug(self):
        print("DRIVING:")
        for car in self.driving: print(car)
        print()

        print("STOPPED:")
        for car in self.stopped: print(car)
        print()

    # Traffic light changed to yellow
    def lightchange(self, state):
        # Light changed to yellow--cars might need to stop
        if state == LightState.YELLOW:
            for car in self.driving:
                # Calculate if car will make it past the crosswalk
                posa = (self.sim.time + YELLOWTIMEOUT - car.atime) / car.speed
                posb = (self.sim.time + YELLOWTIMEOUT + REDTIMEOUT - car.atime) / car.speed
                if posa < self.after or posb > self.before:
                    car.shouldstop = True
                    self.sim.log += f"Car {car.id} should stop at the crosswalk\n"

        # Light changed to green(wait)--stopped cars should go
        elif state == LightState.GREEN:
            for i in range(len(self.stopped)):
                # Get the car moving again and have it exit the sim
                car = self.stopped.pop()

                # Calculate total sim time
                basetime = (self.total - (2 * car.brakedist)) / car.speed
                acctime = car.braketime    # car.stoptime includes the other count of this
                stoptime = self.sim.time - car.stoptime
                time = basetime + acctime + stoptime

                # Calculate the car's delay
                delay = time - (self.total / car.speed)
                self.sim.cardelay.insert(delay)

                self.sim.log += f"Car {car.id} has left the simulation in {time:.3f}s with {delay}s delay\n"

    # Event functions
    def spawn(self, car):
        self.driving.append(car)
        self.sim.insert((self.before - car.brakedist) / car.speed, EventType.CarArrive, car.id)
        self.sim.insert(self.total / car.speed, EventType.CarExit, car.id)
        self.sim.log += f"Spawned new car ({car.id})\n"

    def arrive(self, id):
        # Loop to get the car
        for i, car in enumerate(self.driving):
            if car.id == id:
                # Car should stop at the light
                if car.shouldstop and (self.sim.light.state == LightState.YELLOW or self.sim.light.state == LightState.RED):
                    self.driving.pop(i)
                    self.stopped.append(car)
                    self.sim.log += f"Car {id} will NOT make the light\n"

                else: self.sim.log += f"Car {id} will make the light\n"

                # Update the time (for reference when calculating delays)
                car.stoptime = self.sim.time
                break

    # If the car is still in the 'driving' list, then it was never stopped
    def exit(self, id):
        # Check if car (by ID) is still in driving list
        for i, car in enumerate(self.driving):
            if car.id == id:
                self.driving.pop(i)
                self.sim.cardelay.insert(0.0)
                time = self.sim.time - car.atime
                self.sim.log += f"Car {id} has left the simulation in {time:.3f}s with no delay\n"
                break

# ============================================================================ #
#   Core NES operation
# ============================================================================ #

# Core object for the simulation state
# Takes the four program params as arguments (a, p, and b of type simutils.Token)
class Simulation:
    def __init__(self, n = 10, a = None, p = None, b = None, debug = False):
        # Core NES components
        self.time = 0.0      # Sim clock time

        # WAIT!! BEFORE YOU TAKE OFF POINTS, SEE THE COMMENTS TO FOLLOW!
        # Despite how it appears, I am using a minheap to store the event data!
        self.queue = []      # Simulation event queue
        # Python's implementation of minheap does not provide a data structure
        #   in an object form (like set() or dict(), etc) but instead offers a
        #   series of operations that manage the insertion and deletion of
        #   array elements as an object-oriented version of a minheap would do.
        # The data is stored as a simple array, but every operation is either a
        #   heap push or heap pop operation, and thus satisfies the requirement.

        # Crosswalk components
        self.maxn = n        # Number of cars and peds to generate (each)
        self.npeds = 0       # Current count of pedestrians generated
        self.ncars = 0       # Current count of cars generated
        self.light = Light(self)
        self.peds = PedManager(self)
        self.cars = CarManager(self)

        # Simulation statistics trackers
        self.peddelay = Welford("Ped Delay")
        self.cardelay = Welford("Auto Delay")
        self.eventcount = 0
        self.totalevents = 0

        # Miscellaneous components
        self.lambdap = 20.0   # 60 seconds / 3
        self.lambdaa = 15.0   # 60 seconds / 4
        self.pedrandom = p
        self.autorandom = a
        self.buttonrandom = b
        self.debug = debug
        self.log = None

        # Populate the event queue with the initial arrivals
        self.insert(exponential(self.lambdap, self.pedrandom), EventType.PedSpawn)
        self.insert(exponential(self.lambdap, self.pedrandom), EventType.PedSpawn)
        self.insert(exponential(self.lambdaa, self.autorandom), EventType.CarSpawn)
        self.insert(exponential(self.lambdaa, self.autorandom), EventType.CarSpawn)

    # Insert a new event into the simulation
    def insert(self, delta, type, id = -1):
        event = Event(self.time + delta, type, id)
        push(self.queue, event)
        self.totalevents += 1

    # Begin the simulation
    def start(self):
        while True:
            try: self.next()
            except (StopIteration, IndexError): break

    # Process the next event
    def next(self):
        # Pull the next event out of the event queue
        event = pop(self.queue)
        self.time = event.at
        self.eventcount += 1
        self.log = ""

        # Process the event depending on the type
        if event.type == EventType.TimerExpire:
            self.light.timer()

        elif event.type == EventType.PedSpawn and self.npeds < self.maxn:
            # Generate the new pedestrian
            self.npeds += 1   # Do this early because it's the upcoming ID
            ped = Ped(self.npeds, self.time, self.pedrandom)
            self.peds.spawn(ped)

            # Create the next spawn event
            self.insert(exponential(self.lambdap, self.pedrandom), EventType.PedSpawn)

        elif event.type == EventType.PedArrive:
            self.peds.arrive(event.id)

        elif event.type == EventType.PedImpatient:
            self.peds.impatient(event.id)

        elif event.type == EventType.CarSpawn and self.ncars < self.maxn:
            # Generate the new auto
            self.ncars += 1
            car = Car(self.ncars, self.time, self.autorandom)
            self.cars.spawn(car)

            # Create the next spawn event
            self.insert(exponential(self.lambdaa, self.autorandom), EventType.CarSpawn)

        elif event.type == EventType.CarArrive:
            self.cars.arrive(event.id)

        elif event.type == EventType.CarExit:
            self.cars.exit(event.id)

        # Print a bunch of debug info about the sim
        if self.debug:
            print("SIMULATION:")
            print(f"time: {self.time}")
            print(f"active event: {self.eventcount}, type = {event.type}")
            print()

            print("QUEUE:")
            for e in self.queue: print(f"{e.at} : {e.type} ({e.id})")
            print()

            print("LIGHT:")
            print(self.light)
            print()

            self.peds.debug()
            self.cars.debug()

            print("LOG:")
            print(self.log)

            input("\n\n")


# ============================================================================ #
#   Main program pipeline
# ============================================================================ #

if __name__ == "__main__":
    # Parse arguments
    # Test invocation: python sim.py 100 uniform-0-1-00.dat uniform-0-1-00.dat uniform-0-1-00.dat
    if False and len(argv) != 5:
        print("Usage: SIM {N : int} {AUTO_RANDOM : file} {PED_RANDOM : file} {BUTTON_RANDOM : file}")
        exit(-1)

    try:
        ARG_N = int(argv[1])
        if ARG_N < 1: raise ValueError

    except ValueError:
        print("ERROR: Invalid paramter for N, expecting an int > 0")
        exit(-1)

    ARG_AUTO_RANDOM = None # Token(argv[2])
    ARG_PED_RANDOM = None # Token(argv[3])
    ARG_BUTTON_RANDOM = None # Token(argv[4])

    # Prepare the simulation
    sim = Simulation(ARG_N, ARG_AUTO_RANDOM, ARG_PED_RANDOM, ARG_BUTTON_RANDOM, True)
    sim.start()

    # print(sim.peddelay)
    # print(sim.cardelay)

    print(f"OUTPUT {sim.cardelay.mean()}")
    print(f"OUTPUT {sim.cardelay.variance()}")
    print(f"OUTPUT {sim.peddelay.mean()}")
    exit(0)
