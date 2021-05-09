""" math3D.py - various helpers for 3D activities that might be shared between classes."""
import numpy as np

# Types
FLOAT_T = np.float32
ID_T    = np.int32
GLIDX_T = np.uint32

# Consts
TWO_PI = 2.0 * np.pi

def genRotMat( axis, angle, degrees=False ):
    """
    Generate a rotation matrix. Very simple and naive implementation.
    Args:
        axis: (str) Axis of rotation (X, Y, or Z)
        angle: (float) Angle of rotation
        degrees: (bool) Flag that we're dealing with degrees, not radians

    Returns:
        mat: (ndarray) 4x4 rotation matrix for use with RT matrices directly
    """
    angle = np.deg2rad( angle ) if degrees else angle
    axis = axis.upper()
    ret = np.eye( 4, dtype=FLOAT_T )

    ca = np.cos( angle )
    sa = np.sin( angle )

    if (axis == "X"):
        mat = [ [ 1.0, 0.0, 0.0 ],
                [ 0.0,  ca, -sa ],
                [ 0.0,  sa,  ca ] ]
    elif (axis == "Y"):
        mat = [ [  ca, 0.0,  sa ],
                [ 0.0, 1.0, 0.0 ],
                [ -sa, 0.0,  ca ] ]
    elif (axis == "Z"):
        mat = [ [  ca, -sa, 0.0 ],
                [  sa,  ca, 0.0 ],
                [ 0.0, 0.0, 1.0 ] ]
    else:
        mat = np.eye( 3, dtype=FLOAT_T )

    ret[:3,:3 ] = np.asarray( mat, dtype=FLOAT_T )

    return ret


def genPerspProjectionFrust( h_fov, aspect, near_clip, far_clip ):
    """
    Generate an OpenGL compatible Perspective Projection matrix, from the frustum described by the parameters.
    Args:
        h_fov: (float) Horizontal Field of View (radians)
        aspect: (float) Sensor Aspect ratio
        near_clip: (float) Near Clipping plane
        far_clip: (float) Far clipping plane

    Returns:
        projection matrix: (ndarray) 4x4 Projection Matrix
    """
    ymax = near_clip * np.tan( np.deg2rad( h_fov ) / 2.0 )
    xmax = ymax * aspect
    return genPerspProjectionPlanes( -xmax, xmax, -ymax, ymax, near_clip, far_clip )


def genPerspProjectionPlanes( left, right, base, top, near, far ):
    """
    Generate an OpenGL compatible Perspective projection matrix, bounded by the planes described in the parameters.
    Args:
        left: (float) Left extent in NDC
        right: (float) Right extent in NDC
        base: (float) Bottom extent in NDC
        top: (float) Top extent in NDC
        near: (float) Near Clipping plane in NDC
        far: (float) Far Clipping plane in NDC

    Returns:
        projection matrix: (ndarray) 4x4 Projection Matrix
    """
    rml = right - left
    tmb = top - base
    fmn = far - near
    tnr = 2.0 * near
    return np.array( (
        ( tnr / rml,       0.0, (right + left) / rml,              0.0),
        (       0.0, tnr / tmb,   (top + base) / tmb,              0.0),
               (0.0,       0.0,  -(far + near) / fmn, -far * tnr / fmn),
        (       0.0,       0.0,                 -1.0,              0.0),
    ), dtype=FLOAT_T )


def genOrthoProjectionPlans( left, right, base, top, near, far ):
    """
    Generate an OpenGL compatible Orthogrphic projection matrix, bounded by the planes described in the parameters.
    Args:
        left: (float) Left extent in NDC
        right: (float) Right extent in NDC
        base: (float) Bottom extent in NDC
        top: (float) Top extent in NDC
        near: (float) Near Clipping plane in NDC
        far: (float) Far Clipping plane in NDC

    Returns:
        projection matrix: (ndarray) 4x4 Projection Matrix
    """
    rml = right - left
    tmb = top - base
    fmn = far - near
    return np.array( (
        (2.0 / rml,       0.0,        0.0, -(right + left) / rml),
        (      0.0, 2.0 / tmb,        0.0,   -(top + base) / tmb),
        (      0.0,       0.0, -2.0 / fmn,   -(far - near) / fmn),
        (      0.0,       0.0,        0.0,                   1.0),
    ), dtype=FLOAT_T )