# midget
An Open Source MoCap system.

_We’re dedicated to a mission beyond our ability._

## Rational
I want to emulate the very best features of Giant, Vicon IQ, and the close seconds from Blade and Cortex in an Open Source non-profit system.  With commercial MoCap systems costing no less than $1000/camera, rpi based systems costing $70 per camera could be a great competitor... and open the possibility of MoCap based gait analysis and diagnostics in developing nations - who simply can't afford a $70k bottom end solution.  There is also an interesting possibility for home-use systems - possibly for AR/VR Hobbiests, Indy-games, or even making Erotic Animations for Second-Life _(you know who you are)_ - which are an improvement over the crop of shoddy inertial systems that have sprouted like muchrooms in recent years.

## Philosophy
I hope to follow the 'UNIX Philosophy' - Individual small tools who are really good at one job only; creating human readable files; expecting outputs to flow into inputs where possible.

The core tennet is so simple, it's laughable.  We are tracking something, with a volume, which has markers attached.  For a human, we cannot see through the volume.  Any camera viewing the scene with a trackable object needs to ascribe an identity to any detection it sees.  Detections could be 'true' (from a marker), or 'false' (from water bottles, lights, shiny stuff in the scene).  Labelling, and then solving the skeleton's pose to satisy, 2D views means all captured data is used to solve the skeleton - Some times called "1-Ray" Solving.  "Tradional" MoCap systems depend on solving to labeled 3D reconstructions, and totally ignore the posing of the model, the ability of the model to acelerate between frames to satisfy proposed solutions, the fact a tracked object is solid, Single ray data.

## MoCap Operator's wish list
For years I've wanted to pick a single 2D Detection in a camera view and ascribe an identity to it, and have this either contribute to the solve, or discipline a 'fill'.  For years I've wanted to be able to do a system calibration after the last take, and "back apply" this to the take and get the best possible data.  For years I've wanted to be able to capture the realtime durring a shoot and use this as a basis for the post-processing.  For years I've wanted to selectivly re-track a single limb segment (say, after a death sequnce) without retracking the entire performer or take.

Capture Wish list:
* Capture all assets into single capture folder, not scatter gun them across the filesystem _(looking at you Shogun)_
* Realtime ROMing
* Realtime ROM recovery - with other Objects in the scene
* Arm -> Capture -> Cut workflow
* Non-destructive Solver reset during recording
* Auto ID Props from 'aware' database
* Associate Props with performers
* Interactive "Action"/"Cut" point logging durring recording

Post Wish List:
* Realtime recorded
* Realtime-retrack
* 1-Ray labelling
* Selective re-tracking of Subjects
* * Selective Labelling of markers
* Good Velocity / Cliff limits when labelling
* "Long operation complete" hint sound effect
* Posable skeleton to boot tracking
* Co-articulated joints
* limb segment inertia factored into tracking / prediction / solving
* and many more...

## Installing
We are running on Python 3, currently developing on 3.7.2.  To get the sources and possibly contribute, you'll need git - why else are you here?  Get git on Windows from https://gitforwindows.org/.  Pick an easy to find folder to put the git repos into, I've taken to using 'C:\code' or '/code' as my usual repo.  `git clone https://github.com/bit-meddler/midget.git` (and `git clone https://github.com/bit-meddler/rpiCap.git` for the pi Camera) in there.  To get the dependancies, you should be able to just `pip install -r Requirements.txt` from the project root (make sure it's the right pip for the Python3 interpreter).

### First Run
Just to prove it actually does something remotly like a MoCap system, open a terminal/cmd window and cd into midget/Python/Apps, then run `python simArbiter.py` this will simulate a 10 camera MoCap system, and play back a wand wave at 25fps.  You can experiment with the arguments, add `-r 10 -k 1` to play back more slowly (10fps).

With an Arbiter running, you can launch the 'Camera Control UI' from midget/Python/Experiments.  This is getting most active development as to make a MoCap camera you need good instrumentation to see if it's working, and to start thinking about a camera calibration routine you need to visualize a wand wave and see the results of wand detection, and finally visualize the 3D positions of the Calibrated cameras.

As the project develops Core functions will make their way into Rust or C++.  We'll cross that bridge later.

## The Plan (simplified)
1. Collect/Visualize data
2. Caliibrate camera system _<- we are here_
3. Reconstruct points
4. Model representation
5. Track model through sequence (manual ID)
6. Auto ID subject in scene, boot model tracking

Before we're even in a position to collect the data and work out a calibration system, it seems we need a whole load of UI Developing.

## Apps we need
1. Arbiter
2. Camera Config / Monitoring
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
