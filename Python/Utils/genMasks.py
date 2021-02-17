""" Generate the code for mask region's "NodeTrates", and their register addresses. """
num = 16
axis = ["x", "y", "m", "n"]
human = ["Left", "Top", "Right", "Bottom"]

for i in range( num ):
    for ax, hm in zip( axis, human ):
        print( """    "maskzone{0:0>2}{1}": CameraTraits( "maskzone{0:0>2}{1}", 0, 0, 4096, int,
                                 value=None,
                                 units="Pixels",
                                 human_name="Mask Zone {0:0>2} {3}",
                                 desc="Mask {0:0>2} position {2}" ),
               """.format( i+1, ax, hm, ax.upper() ) )
        
reg = 298
for i in range( num ):
    for ax in axis:
        reg += 2
        print( """        "maskzone{0:0>2}{1}" : ( {2}, 2, True ),""".format( i+1, ax, reg ) )
