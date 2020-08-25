"""
MoCap Camera / control unit communications

Classes at the module level are architecture agnostic.  So a concrete example, piCam is implementation info about a piCam
piComunicate is the communication routines that are specific to that camera.  In the future there might be an "odroidCam" or
an "arduinoCam" which will have different implementation and communication methods.  Perhaps one gets C&C over telnet.
That is why C&C is done in a "Platonic Language" that is not related to implementation.
"""
class CameraTraits( object ):
    """ Object describing controllable traits of a camera. It holds GUI presentable data
        like a human readable name, description etc, and implementation specific data
        like how to set the value (which will be very camera dependant)

        mode is a combination of Read, Write, Advanced, eXclude = "rwa", "rx"
    """
    def __init__(self, name, default, min, max, cast, value=None, units=None, human_name=None, desc=None, mode=None ):
        # required
        self.name = name
        self.default = default
        self.min = min
        self.max = max
        self.dtype = dtype

        # interface sugar
        self.value = value or default
        self.units = units or ""
        self.human_name = human_name or name
        self.desc = desc or ""
        self.mode = mode or "rw"

    def isValid( self, candidate ):
        """ Basic Validation, override for special cases """
        return ( (candidate <= self.max) and (candidate >= self.min) )


class SysManager( object ):
    """
    Class to manage system topology, hold camera table. manage camera_ids, know camera types

    Assumptions: IP address is fixed so camera type is consistent between sessions
    """

    def __init__( self ):
        self._reset()

    def _reset( self ):
        self.cam_dict = {}  # ip -> id
        self.rev_dict = {}  # id -> ip
        self.num_cams =  0  # count of all cameras
        self.sys_hash =  0  # if topology changes, this does too
        self.old_hash = {}  # record of previous "state" (Cam order, list of cam ips)
        self.bad_cams = []  # list of cameras that may be at fault
        self.last_dgm = {}  # timestamp (BCD cast as I) of last communication from a camera
        self.cam_type = {}  # ip -> camera data (family, type, resolution)

        self.current_time = 0

    def getCamId( self, cam_ip, timestamp ):
        """
        Get a camera's ID.  if it's a new camera, update the table and announce a state change.
        Also note the last contact time for the camera, could help with diagnostics.
        This gets run a lot!

        :param cam_ip: Camera ip
        :return: id, state_changed
        """
        state_changed = False
        try:
            cam_id = self.cam_dict[ cam_ip ]
        except KeyError:
            # New Camera Discovered, add to cam list
            cam_id = self.num_cams  # 0 index :)
            self.num_cams += 1
            self.cam_dict[ cam_ip ] = cam_id
            self.rev_dict[ cam_id ] = cam_ip
            self._updateHash()
            state_changed = True

        self.last_dgm[ cam_id ] = timestamp
        return (cam_id, state_changed)

    def _updateHash( self ):
        self.sys_hash += 1
        self.old_hash[ self.sys_hash ] = self.getCamList()

    def flagBadId( self, cam_id ):
        if (not cam_id in self.bad_cams):
            self.bad_cams.append( cam_id )
        # leave it to the UI?

    def _load( self, camip_list ):
        # setup ids from the given list, fully resets state
        self._reset()
        self.cam_dict = { ip: n for n, ip in enumerate( camip_list ) }
        self.rev_dict = { val: key for key, val in self.cam_dict.items() }
        self.num_cams = len( self.cam_dict )

    def loadJSON( self, file_fq ):
        pass

    def saveJSON( self, file_fq ):
        # make a dict of camera data
        dat = { }
        for ip, id in self.cam_dict.items():
            dat[ ip ] = {
                "ID"    : id,
                "FAMILY": self.cam_type[ ip ][ 0 ],
                "TYPE"  : self.cam_type[ ip ][ 1 ],
                "SENSOR": self.cam_type[ ip ][ 2 ],
            }

        sys_cfg = json.dumps( dat, indent=4, sort_keys=True )

        with open( file_fq, "w" ) as fh:
            fh.write( sys_cfg )

    def remarshelCameras( self ):
        """
        Sort the cameras to be ordered by ip.  This will invalidate and frame assembly going on and corrupt your
        calibration. use the supplied "rename map" to fix you calibration.
        :return: (dict) rename_map - lut of old to new camera IDs
        """
        # ? Lock ?
        new_dict = { ip: n for n, ip in enumerate( sorted( self.cam_dict.keys() ) ) }
        rename_map = { val: new_dict[ key ] for key, val in self.cam_dict.items() }
        self.cam_dict.clear()
        self.cam_dict = new_dict
        self.rev_dict = { val: key for key, val in self.cam_dict.items() }
        self._updateHash()

        return rename_map

    def getCamList( self ):
        return (c for c in sorted( self.cam_dict.items(), key=lambda x: x[ 1 ] ))

