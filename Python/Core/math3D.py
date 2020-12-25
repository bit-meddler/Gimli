import numpy as np

# Types
FLOAT_T = np.float32
ID_T    = np.int32

# Consts
TWO_PI = 2.0 * np.pi

def genRotMat( axis, angle, degrees=False ):
    angle = np.deg2rad( angle ) if degrees else angle
    axis = axis.upper()
    ret = np.eye( 4, dtype=np.float32 )

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
    ymax = near_clip * np.tan( np.deg2rad( h_fov ) / 2.0 )
    xmax = ymax * aspect
    return genPerspProjectionPlaines( -xmax, xmax, -ymax, ymax, near_clip, far_clip )


def genPerspProjectionPlaines( left, right, base, top, near, far ):
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


def genOrthoProjectionPlains( left, right, base, top, near, far ):
    rml = right - left
    tmb = top - base
    fmn = far - near
    return np.array( (
        (2.0 / rml, 0.0, 0.0, -(right + left) / rml),
        (0.0, 2.0 / tmb, 0.0, -(top + base) / tmb),
        (0.0, 0.0, -2.0 / fmn, -(far - near) / fmn),
        (0.0, 0.0, 0.0, 1.0),
    ), dtype=FLOAT_T )