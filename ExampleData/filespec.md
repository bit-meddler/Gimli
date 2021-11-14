**Example MoCap Data - File Structure**

The supplied files are raw mocap data, stored as Pickeled lists of 'frame data'.

```
import pickle

with open( "calibration.pik", "rb" ) as fh:
	frames = pickle.load( fh )
```
Each `frame` in this structure is a tuple with 3 elements, being a stride list,
the detection data (Centroids), and ID data.

`strides, dets, labels = frames[ 0 ]`

The `strides` describe what "slice" of the `dets` are detections for each camera.
if `s_in` and `s_out` are the same, there are no detections for the given camera,
and `s_out` minus `s_in` would give the number of detections. 

```
num_cams = len( strides ) - 1

n = 2
cam_n_data = dets[ strides[n] : strides[n+1] ]

# walking through all camera's data
for cam_id in range( len( strides ) - 1 ):
    s_in, s_out = strides[ cam_id ], strides[ cam_id + 1 ]
    num_dets = s_out - s_in
```

Detections are in 'NDC' form, normalized from -1 to +1 in their largest axis.
The small axis is scaled and recentered such that principle point (optical center
of image) is nominally at (0,0).  Square pixels are enforced.

The labels are in lock-step with the `dets` data, so a label for any given detection
will have the same index as the detection in the dets list.

```
# alternate striding
for cam_id, (s_in, s_out) in enumerate( zip( strides[:-1], strides[1:] ) ):
    data = dets[ s_in : s_out ]
    IDs = labels[ s_in : s_out ]

    for x, y, radius in data:
        # ToDo: Some MoCap

```