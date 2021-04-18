# Workaround not being in PATH
import os, sys
_git_root_ = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ) ) )
CODE_PATH = os.path.join( _git_root_, "Gimli", "Python" )
OUT_PATH  = os.path.join( _git_root_, "Gimli", "ExampleData" )
DATA_PATH = os.path.join( _git_root_, "rpiCap", "exampleData" )
sys.path.append( CODE_PATH )

import numpy as np
import pickle

def packFrames( target ):
    frames = []
    # load up the replay files
    cams = []
    for i in range( 10 ):
        cam_fq = os.path.join( DATA_PATH, target + ".a2d_cam{:0>2}.pik".format( i ) )
        with open( cam_fq, "rb" ) as fh:
            cams.append( pickle.load( fh ) )

    # repack each frame
    num_frames = len( cams[0] )
    empties = 0
    pixel_scale = 2.0 / 1024.0
    for i in range( num_frames ):
        dets = []
        stride = [0]
        for j in range( 10 ):
            rad = np.random.uniform( 0.455, 7.5, 1 )[0]
            cam_frame = [ [x, y, rad] for x, y in cams[j][i] ] # add a radius col
            dets.extend( cam_frame )
            stride.append( stride[-1] + len(cam_frame) )

        # I'll have that as NumPy, thanks
        np_frame = np.asarray( dets, dtype=np.float32 )
        
        # Convert to NDC (should be done in DetMan / SysMan)
        try:
            np_frame *= pixel_scale # all pixel united info is normalized
            np_frame[:,:2] -= 1. # re-center
        except:
            empties += 1

        frames.append( ( stride, np_frame.tolist(), np.zeros((np_frame.shape[0],),dtype=np.int).tolist() ) )

    print( "{} Empty frames".format( empties ) )
    return frames

recording = "calibration"
out_fq = os.path.join( OUT_PATH, recording + ".pik" )
frames = packFrames( recording )
pickle.dump( frames, open( out_fq, "wb" ) )
