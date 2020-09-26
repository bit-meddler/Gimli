# midget
An Open Source MoCap system.

## Rational
OK, so...  LEI, born of Giant, born of Acclaim, *is* the best MoCap system in the world.  Nobody completly knows why.  I want to emulate the very best features of Giant, Vicon IQ, and the close seconds from Blade and MAC in an Open Source non-profit system.  With commercial MoCap systems costing no less than $1000/camera, rpi based systems costing $70 per camera could be a great competitor... and open the possibility of MoCap based gait analysis and diagnostics in 3rd world and developing nations - who simply can't afford a $70k bottom end solution.

## Philosophy
A tiny part of what makes Giant great is the 'UNIX Philosophy'.  Individual small tools who are really good at one job only; creating human readable files; expecting outputs to flow into inputs.

As I interpret it, the very first giant iterations were basicly rotoscoping tools.  Four _interlaced_ CCTV cameras - standard definition - running at 59.94 fps, with a continious spotlight.

A dimentionality reduction of the tracking model both reduces the IK solver's work load, and enhances the 'asthetics' of the solution.

The core tennet is so simple, it's laughable.  We are tracking something, with a volume, which has markers attached.  We cannot see through the volume.  Any camera viewing the scene with a trackable object needs to ascribe an identity to any detection it sees.  Detections could be 'true' (from a marker), or 'false' (from water bottles, lights, shiny stuff in the scene).  Labelling, and then solving the skeleton's pose to satisy, 2D views means all captured data is used to solve the skeleton.  "Tradional" MoCap systems depend on solving to labeled 3D reconstructions, and totally ignore the posing of the model, the ability of the model to acelerate between frames to satisfy proposed solutions, the fact a trackedobject is solid, Single ray data.

## Installing
We are running on Python 3, currently developing on 
3.7.2.  To get the dependancies, you should be able to 
`pip install -r Requirements.txt`

As the project develops Core functions will make their 
way into rust or C++.  we'll cross that bridge later.

## The Plan
Errrrrrrr. First collect some data.
1. collect data
2. caliibrate camera system
3. reconstruct points
4. model representation
5. track model through sequence
6. ID subject in scene, boot model tracking

