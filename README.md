# Gimli
An Open Source MoCap system.

_"We’re dedicated to a mission beyond our ability"._

## Current Status
We're still a long way from anything like a remotely working application, as I need the help of more experienced developers (Qt MVC, OpenGL), and Mathematicians (Computer Vision, Linear algebra, Optimization).  If this is you, why not say 'Hello' in the [discussion](https://github.com/bit-meddler/Gimli/discussions).

## Rational
I want to emulate the very best features of Giant, Vicon IQ, and the close seconds from Blade and Cortex in an Open Source non-profit system.  With commercial MoCap systems costing no less than $1000/camera, rpi based systems costing $70 per camera could be a great competitor... and open the possibility of MoCap based gait analysis and diagnostics in developing nations - who simply can't afford a $70k bottom end solution.  There is also an interesting possibility for home-use systems - possibly for AR/VR Hobbyists, Indy-games, or even making Erotic Animations for Second-Life _(you know who you are)_ - which are an improvement over the crop of shoddy inertial systems that have sprouted like mushrooms in recent years.  Oh and it's a great chance to Stick-it-to-the-Man as well.

## Philosophy
I hope to follow the 'UNIX Philosophy' - Individual small tools who are really good at one job only; creating easily readable files, preferably text-based; expecting outputs to flow into inputs where possible.

The core tenet is so simple, it's laughable.  We are tracking something, with a volume, which has markers attached.  For a human, we cannot see through the volume.  Any camera viewing the scene with a trackable object in it needs to ascribe an identity to any detections it sees.  Detections could be 'true' (from a marker), or 'false' (from water bottles, lights, shiny stuff in the scene).  Labelling, and then solving the skeleton's pose to satisfy 2D views means all captured data is used to solve the skeleton - Some times called "1-Ray" Solving.  "Traditional" MoCap systems depend on reconstructing all detections to 3D reconstructions, labelling then solving - and totally ignore the posing of the model, the fact a tracked object is solid, Single ray data.  Also no consideration is given to how plausible the new Labelling/Solve is when compared to prior frames, factoring in things like the inability of the model to accelerate between frames to satisfy proposed solutions, or a 'pain factor' the Subject might be experiencing if they attempted to bust some of the moves a proposed solution suggested.  It's also a good chance that the Performer's skeleton won't change shape during the take.

There is a lot of documentation and discussion of MoCap approaches in the [Wiki](https://github.com/bit-meddler/Gimli/wiki)

## Licence
Not sure, GPL3 I guess.

## Installing
We are running on Python 3, currently developing on 3.7.2.  To get the sources and possibly contribute, you'll need git - why else are you here?  Get git on Windows from https://gitforwindows.org/.  Pick an easy to find folder to put the git repos into, I've taken to using 'C:\code' or '/code' as my usual repo.  `git clone https://github.com/bit-meddler/Gimli.git` (and `git clone https://github.com/bit-meddler/rpiCap.git` for the pi Camera) in there.  To get the dependencies, you should be able to just `pip install -r Requirements.txt` from the project root (make sure it's the right pip for the Python3 interpreter).

### First Run
Just to prove it actually does something remotely like a MoCap system, open a terminal/cmd window and cd into Gimli/Python/Apps, then run `python simArbiter.py` this will simulate a 10 camera MoCap system, and play back a wand wave at 25fps.  You can experiment with the arguments, add `-r 10 -k 1` to play back more slowly (10fps).

With an Arbiter running, you can launch the 'Camera Control UI' from Gimli/Python/Apps.  This is getting most active development as to make a MoCap camera you need to: be able to tell it what to do; have good instrumentation to see if it's working; to start thinking about a camera calibration routine you need to visualize a wand wave and see the results of wand detection; and finally visualize the 3D positions of the Calibrated cameras, perhaps even the 3D position of the wand.

As the project develops Core functions will make their way into Rust or C++.  We'll cross that bridge later.

## The Plan (simplified)
1. Collect/Visualize data
2. Calibrate camera system _<- we are here_
3. Reconstruct points
4. Model representation
5. Track model through sequence (manual ID)
6. Auto ID subject in scene, boot model tracking

Before we're even in a position to collect the data and work out a calibration system, it seems we need a whole load of UI Developing.

## Apps we need
1. Arbiter
2. Camera Config / 2D Monitoring
3. Calibration & Visualization (2D/3D)
4. CLI Calibration
5. 3D Scene Management
6. Reconstructions in 3D
7. Animations / Skeletons in 3D
8. Skeleton creation / visualization
9. IK Solver _(easy, right?)_
10. Pose Simulation
11. Tracking Tool
12. Filtering Tool
13. Exporter to known format
14. Retargeting
15. Realtime(!)
