## Course Affiliation

This project was written for CSCI423: Computer Simulation at Colorado School of Mines.  
The purpose of this project was to practice using the principles of Discrete Event Simulations we had been learning in class.

This code is free for you to explore and use, but I request that it only be used for non-profit/educational purposes. Furthermore, if by chance you find yourself working on the same project, I strongly recommend that you avoid reuse of any of this code.

## Project Description

< TODO - Find project writeup >

## Running the Program

One of the additional requirements for this project was building it such that it
could be ran by a linux machine via the grader script. As such, this project has
a small `Build.sh` script to create a basic SIM executable.  
To run the program, run `sim.py` with Python 3, or run `Build.sh` followed by `./SIM`.

## Submission Readme

> Some notes:
I was struggling with permissions on build.sh. I think I got it to work, but on
chance something still goes awry, 'chmod +x Build.sh' seems to do the job.
>
> I have also observed that many of the first cars in the simulation drive past
the crosswalk before any pedestrians arrive, giving many cars a delay of 0. I
fear that this may skew the results, but I am unsure if this is accounted for by
the grader script.
>
>
> Code 'pointers':
>
> Usage of Welford's Equations
I define my Welford object in simutils.py, line 69.
I create two Welford members of my sim objects in sim.py, lines 365 and 366.
I put data into the Pedestrian Welford object in sim.py, line 222.
I put data into the Automobile Welford object in sim.py, lines 297 and 330.
>
> Exponential(u) random variate
I define the exponential(u) function in simutils.py, line 190.
I insert my initial events in sim.py, lines 380 - 383.
Every subsequent event is generated in sim.py, line 416 or 431.
>
> Prioritized event list
I define my event queue in sim.py, line 348.
^^An important note with this, however, is that this line alone is not
descriptive enough. I decided to use a min heap to store my event queue for this
project, however Python's implementation of min heaps is a library with an array
function set, as a simple list is the core of a minheap. By exclusively
accessing this array with the functions in the library, the O(1) pop, and
O(log n) insert complexities of a min heap are maintained. See sim.py, lines 388
and 400.

## Additional Assumptions

Crosswalk sim questions:  
 - Does street side matter?  
     I.E. I could begin my sim by enqueuing two 'pedspawn' events (one for each side)
     and let it run without ever explicitly saying technically which side they came from.
     That said, I suspect that dropping this to one 'pedspawn' event *would* change
     the results of the simulation, but I can't reason exactly why...  
     (assuming no)  

 - If a pedestrian arrives at the button when the light is green that *could* make it
     across the crosswalk, BUT 20 peds are already crossing, do they begin their
     impatient timer on this arrival condition?  
     (assuming yes)  

 - If a pedestrian becomes impatient, do I start a new timer when they go through
     their press routine? (Say the last pedestrian of the simulation is alone and becomes
     impatient, and their P(0) call returned false. Will they be stuck there forever?)  
     (assuming yes)  

 - Does the example grader.sh output have the correct output for the specific parameter
     values we are implementing? I.E. right now even a few trials imply that my curve
     would be skewed from that that is shown in the screenshot.  
     (assuming no)  

 - There appears to be a big discrepancy between the first cars that spawn and the last
     of the pedestrians. Since the stoplight behavior is unaffected, the pedestrians will
     not experience any skew, but I fear that the cars will, because many will pass through
     the light before any pedestrians arrive. Is this accounted for by the grader script?  
     (assuming yes)  

 - When a project has multiple files, Python precompiles them to support the import 'file'
     syntax, which generates a folder with underscores. Will this be counted against me,
     or should I merge the project in to one huge python file?  


Answers:
- NO (impossible condition): Ped requirement 7, at most 20 peds may cross at once:
    Does this mean a new pedestrian could start walking when one gets to the other side?  

- WITHIN CONSTANTS AND DISTRIBUTIONS: What should u be in Exponential(u) arrivals/how
    should I go about determining it?  

- UNDER PROJECT REQUIREMENTS: What does DOC mean? Document code location in readme?  
