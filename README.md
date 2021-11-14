# Gimli
An Open Source MoCap system.

_"Certainty of death. Small chance of success. What are we waiting for?"_

## Current Status
We're still a long way from anything like a remotely working application, as I need the help of more
experienced developers (Qt MVC, OpenGL), and Mathematicians (Computer Vision, Linear algebra,
Optimization).  If this is you, why not say 'Hello' in the
[discussion](https://github.com/bit-meddler/Gimli/discussions).

## Rational
I want to emulate the very best features of Giant, Vicon IQ, and also Blade and Cortex, in an Open
Source system.

With commercial MoCap systems costing no less than $1000/camera, an rpi based system costing ~$70
per camera could be a great alternative, and open the possibility of MoCap based gait analysis and
diagnostics in developing nations - who simply can't afford a $70k bottom-end solution from a
traditional vendor.  There is also an interesting possibility for home-use systems - possibly for
AR/VR Hobbyists, Indy-games, or even making Erotic Animations for Second-Life _(you know who you are)_.
The rpi camera and software solution would be an improvement over the crop of shoddy inertial systems
that have sprouted like mushrooms in recent years.  In the Open-Source world the deliniation between
developer and user is very narrow, if you want a feature, you could make a branch, code it yourself
and make a pull request.  No more 6-monthly Velvet curtain relases from the traditional vendor who
doesn't ever listen to your feature requests.

_Oh and it's a great chance to Stick-it-to-the-Man as well._

## Philosophy
I hope to follow the 'UNIX Philosophy' - Individual small tools who are really good at one job only;
creating easily readable files, preferably text-based; expecting outputs to flow into inputs where
possible.

The core tenet is so simple, it's laughable.
- We are tracking something, with a physical presence, which has some markers attached.  For a human,
we cannot see through their body. Any camera viewing the scene with a trackable object in it needs
to ascribe an identity to any detections it sees. Detections could be _'true'_ (from a marker), or
_'false'_ (from water bottles, lights, shiny stuff in the scene).

- Labelling, and then solving the skeleton's pose to satisfy 2D views means all captured data is 
used to solve the skeleton - Sometimes called "1-Ray" Solving. This could be as simple as using 1-Rays
as an error term in the IK solver, or as complicated as constraining the solve to the ray.
"Traditional" MoCap systems depend on triangulating all detections to 3D reconstructions, labelling 
then solving - and totally ignore: The posing of the model; How 'painful' a pose may be; The fact a
tracked object is solid; Single ray data.

- Also no consideration is given to how plausible the new Labelling/Solve is when compared to prior
frames, factoring in things like the inability of the model to accelerate between frames to satisfy
proposed solutions, or a 'pain factor' the Subject might be experiencing if they attempted to bust
some of the moves a proposed solution suggested. It's also a good chance that the Performer's skeleton
won't change shape during the take.

There is a lot of documentation and discussion of MoCap approaches in the
[Wiki](https://github.com/bit-meddler/Gimli/wiki)

## Licence
After some debate, I have selected the GPLv3 Licence for this project.  The Licence is included in
the root of the Project, and will be referenced in source and resource files going forwards.

## Installing
We are running on Python 3, currently developing on 3.7.2.  To get the sources and possibly
contribute, you'll need git - that's why you're here, right?  Get git on Windows from
https://gitforwindows.org/.  Pick an easy to find folder to put the git repos into, I've taken to
using 'C:\code' or '/code' as my usual repo.  `git clone https://github.com/bit-meddler/Gimli.git`
(and `git clone https://github.com/bit-meddler/rpiCap.git` for the rpi Camera) in there.  To get
the dependencies, you should be able to just `pip install -r Requirements.txt` from the Gimli project
root (make sure it's the right pip for the Python3 interpreter).  An Advanced user is free to use
a virtual environment if they so wish.

### First Run
Just to prove it actually does something remotely like a MoCap system, open a terminal/cmd window
and cd into Gimli/Python/Apps, then run `python simArbiter.py` this will simulate a 10 camera MoCap
system, and play back a wand wave at 25fps.  You can experiment with the arguments, add `-r 10 -k 1`
to play back more slowly (10fps).

With the Arbiter running, you can launch the 'Camera Control UI' from Gimli/Python/Apps.  This is
getting most active development as to make a MoCap camera you need to: be able to tell it what to do;
have good instrumentation to see if it's working; to start thinking about a camera calibration
routine you need to visualize a wand wave and see the results of wand detection; and finally
visualize the 3D positions of the Calibrated cameras, perhaps even the 3D position of the wand.

As the project develops Core functions will make their way into Rust or C++.  We'll cross that bridge
later.

## The Plan (simplified)
1. Collect/Visualize data
2. Calibrate camera system _<- we are here_
3. Triangulate points
4. Model representation
5. Track model through sequence (manual ID)
6. Auto ID subject in scene, boot model tracking

Before we're even in a position to collect the data and work out a calibration system, it seems we
need a whole load of UI Developing.

## Apps we need
1. Arbiter
2. Camera Config / 2D Monitoring
3. Calibration & Visualization (2D/3D)
4. CLI Calibration
5. 3D Scene Management
6. Triangulation in 3D
7. Animations / Skeletons in 3D
8. Skeleton creation / visualization
9. IK Solver _(easy, right?)_
10. Pose Simulation
11. Subject Setup
12. Tracking Tool
13. Filtering Tool
14. Exporter to known formats
15. Retargeting
16. Realtime(!)

## A Note on Coding style
I've got bad eyesight and hate PEP-8. Any kind of brace needs to be padded - that's subscripts (list[ 
index ] or dict[ key ] access), function( calls ) or generators = [ i for i in range( num ) ]. 'if'
or 'while' blocks want Parens touching the keyword `if( (is_clause==1) and (not self.incuringWrath()) )`
enclose sub-clauses in parens as well. Same goes for maths `x = (a + b) * ((c*d) - 1)` please, it helps
you debug, and me or others read and understand it.

We're not coding on an 80 col VT-100, I have rules at 80, 100, 120 cols, and think about continuation
or other alignment things around 121 cols.  If you are developing on an 80 col device and make significant
contribution to Gimli or the rpi Camera, I'll buy you a pi.

Speaking of having abundent screen space, comprehensible variable names please. If you've just
micro-dosed on LSD ` wz[si] -= d2k[ti:]; dxdy_i *= k2f[fi:st-ti]` might be like touching the face of
god, but it does me no good, also we have more than 25 rows, so packing statements onto a single line
is not benefiting mankind.

We're using quite a lot of Qt and OpenCV so I use capitalization conventions close to the C++ Libraries.
```
class PascalCase( object ):

    ALLCAPS_CONSTANT = 3.14159265359
    
    def __init__( self, param, optional_param=None ):
    self.param = param
    self.optional_param = optional_param or self.ALLCAPS_CONSTANT
    self.allways_brace_ifs = True
    
    self._private_like_var = "leading underscore"
    
    snake_case_variable = len( self.param )
    
    pad_subscripts = pad_parens = 2
    
    value = self.param[ pad_subscripts ]
    
    # discarded returns go into an underscore
    _ = self.camalCaseFunction( pad_parens )
    
    # also applis in a comprehension
    self._my_comprehension = [ None for _ in range( snake_case_variable ) ]
    
    def camalCaseFunction( self, value ):    
        if( self.always_brace_ifs ):
            return value
```

For Class or Method documentation I try to follow the Google documentation format.  Python 3 Type
Hinting feels alien at the moment, but I might adopt it in the future.  I anotate the args and returns
with the expected type, and for tuple returns these are expanded and annoated.  This example is
quite good _(Python/Core/labelling.py)_:
```
def labelWandFrame( dets, strides ):
    """
    Labels the whole frame described by the dets array and the stride list.
    ToDo: In the future this could be cheaply parallelized, but not today.

    Args:
        dets     (ndarray): Nx2 array of dets for all cameras
        strides  (ndarray): N+1 array of Stride in/out indexes for the cameras

    Returns:
        label data (tuple)
            ids  (ndarray): Nx1 array of IDs in lock step the the dets,
            report  (list): list of cameras that have been labelled on this frame
    """
    report = []
    ids = np.full( len( dets ), 0, dtype=ID_T )

    for cam, (s_in, s_out) in enumerate( zip( strides[:-1], strides[1:] ) ):
        labels, score = labelWand( dets, s_in, s_out, False )
        if( labels is not None ):
            ids[ s_in : s_out ] = labels
            report.append( cam )

    return (ids, report)
```