import numpy as np
import time


class Edge( object ):

    def __init__( self, source, target, capacity, cost=0 ):
        self.source = source
        self.target = target
        self.capacity = capacity
        self.edge_cost = self.cost = cost
        self.flow = 0
        self.residual = None
        self.isResidual = bool( capacity == 0 )

    def remainingCapacity( self ):
        return self.capacity - self.flow

    def augment( self, delta_flow ):
        self.flow += delta_flow
        self.residual.flow -= delta_flow

    def __str__( self ):
        return "{} {} -> {} | flow = {} | capacity = {} | cost: {}".format(
            "Resi" if self.isResidual else "Edge",
            self.source, self.target, self.flow, self.capacity, self.cost
        )

    def __repr__( self ):
        return "{}<{} -> {}> {} {}".format(
            "R" if self.isResidual else "E", self.source, self.target, self.flow, self.cost
        )


class BellmanFord( object ):

    INF = 0x88888888 # To avoid overflow, set infinity to a big number, but less than a really big number

    def __init__( self, num_nodes ):
        self.num_nodes = num_nodes
        self.source_idx = 0
        self.sink_idx = num_nodes - 1
        self.min_cost = 0
        self.max_flow = 0
        self.graph   = [ [] for _ in range( self.num_nodes ) ]

    def addEdge( self, source, target, capacity,  cost=0  ):
        edge     = Edge( source, target, capacity, cost )
        residual = Edge( target, source, 0, -cost )
        edge.residual = residual
        residual.residual = edge
        self.graph[ source ].append( edge )
        self.graph[ target ].append( residual )

    def solve( self ):
        # Sum up the forward flow on each augmenting path to find the max flow and min cost.
        itercount = 1
        path = self.findAugmentingPath()
        while( len( path ) != 0 ):
            print( path )
            # Find "bottle neck" edge value along this path.
            path_flow = self.INF
            for edge in path:
                path_flow = min( path_flow, edge.remainingCapacity() )
            
            # Retrace path while augmenting the flow
            for edge in path:
                edge.augment( path_flow )
                self.min_cost += path_flow * edge.edge_cost
            
            self.max_flow += path_flow

            path = self.findAugmentingPath() # next path
            itercount += 1
        print( "{} iterations".format( itercount ) )

    def findAugmentingPath( self ):
        # Use the Bellman-Ford algorithm to find an augmenting path through the flow network.

        dist = [ self.INF for _ in range( self.num_nodes ) ]
        dist[ self.source_idx ] = 0
        prev = [ None for _ in range( self.num_nodes ) ]

        # For each vertex, relax all the edges in the graph, O(VE)
        for i in range( 4 ): # max depth - might be a bad optimization
            for source in range( self.num_nodes ):
                for edge in self.graph[ source ]:
                    edge_cost = dist[ source ] + edge.cost

                    if( ( edge.remainingCapacity() > 0) and ( edge_cost < dist[ edge.target ] ) ):
                        dist[ edge.target ], prev[ edge.target ] = edge_cost, edge

        # Retrace augmenting path from sink back to the source.
        path = []
        edge = prev[ self.sink_idx ]
        while( edge is not None ):
            path.insert( 0, edge )
            edge = prev[ edge.source ]

        return path

def createGraphFromDM( dm ):
    news, priors = len( dm ), len( dm[0] )
    num = news + priors + 2
    solver = BellmanFord( num )

    # attach new "nodes" to Source
    node_count = 1
    for i in range( news ):
        solver.addEdge( solver.source_idx, node_count, 1, 0 )
        node_count += 1

    # add weighted candidate edges from news to priors
    off = node_count
    for i in range( 0, news ):
        for j in range( priors ):
            score = dm[ i ][ j ]
            if( score > 0 ):
                solver.addEdge( i+1, off + j, 1, score )

    # hook up the priors to the Sink
    for i in range( priors ):
        solver.addEdge( off + i, solver.sink_idx, 1, 0 )

    return solver


if( __name__ == "__main__" ):
    dm = [ [    2.,  842.,   -1., -1., -1.,  842., -1., -1., -1. ],
           [  962.,    2.,    1., -1., -1., 1802., -1., -1., -1. ],
           [ 1025.,    5.,    2., -1., -1., 1865., -1., -1., -1. ],
           [   -1.,   -1.,   -1.,  2.,  2.,   -1., -1., -1., -1. ],
           [   -1.,   -1.,   -1.,  2.,  2.,   -1., -1., -1., -1. ],
           [  962., 1802.,   -1., -1., -1.,    2.,  1., -1., -1. ],
           [ 1025., 1865.,   -1., -1., -1.,    5.,  2., -1., -1. ],
           [   -1.,   -1.,   -1., -1., -1.,   -1., -1.,  2., -1. ],
           [   -1.,   -1.,   -1., -1., -1.,   -1., -1., -1.,  2. ],
           [ 2017.,  277.,  250., -1., -1., 2377., -1., -1., -1. ],
           [   -1.,   -1., 6641., -1., -1.,   -1., -1., -1., -1. ] ]

    start = time.time()

    test = "NUMPY"

    if( test == "BELL" ):
        n = 5
        
        solver = BellmanFord( n )

        solver.addEdge( solver.source_idx, 1, 4, 10 )
        solver.addEdge( solver.source_idx, 2, 2, 20 )
        solver.addEdge( solver.source_idx, 3, 3, 30 )
        
        solver.addEdge( 1, 2, 2, 10 )

        solver.addEdge( 1, solver.sink_idx, 1, 60 )
        solver.addEdge( 2, solver.sink_idx, 4, 10 )
        solver.addEdge( 3, solver.sink_idx, 4, 10 )

        comp_in  = 0
        comp_off = 0

    elif( test == "BELL2" ):
        n = 8

        solver = BellmanFord( n )

        # Source to candidates
        solver.addEdge( solver.source_idx, 1, 1, 1 )
        solver.addEdge( solver.source_idx, 2, 1, 1 )
        off = 3

        # candidate edges & weights
        solver.addEdge( 1, off + 0, 1,  962 )
        solver.addEdge( 1, off + 1, 1,    2 )
        solver.addEdge( 1, off + 2, 1,    1 )
        solver.addEdge( 1, off + 3, 1, 1802 )

        solver.addEdge( 2, off + 0, 1, 1025 )
        solver.addEdge( 2, off + 1, 1,    5 )
        solver.addEdge( 2, off + 2, 1,    2 )
        solver.addEdge( 2, off + 3, 1, 1865 )

        # priors to Sink
        solver.addEdge( off + 0, solver.sink_idx, 1, 1 )
        solver.addEdge( off + 1, solver.sink_idx, 1, 1 )
        solver.addEdge( off + 2, solver.sink_idx, 1, 1 )
        solver.addEdge( off + 3, solver.sink_idx, 1, 1 )

        comp_in  = 0
        comp_off = 0

    elif( test == "NUMPY" ):

        #dm = np.asarray( dm, dtype=np.float32 )
        #dm = np.flipud( dm )

        solver = createGraphFromDM( dm )

        comp_in  =  1
        comp_off = 12

    elif( test == "FLAT" ):
        solver = BF_Graph( dm )

    solver.solve()

    end = time.time()

    period = end - start
    print( "Max flow: {}, Min cost: {} in {:.3f} secs".format(
        solver.max_flow, solver.min_cost, period )
    )

    encountered_sources = set()
    flowing_sources = set()
    for edges in solver.graph:
        for e in edges:
            if( e.isResidual ):
                continue

            if( (e.source == solver.source_idx) or (e.target == solver.sink_idx) ):
                continue

            if( e.source < e.target ):
                encountered_sources.add( e.source )
                
                if( e.flow > 0 ):
                    print( "{} -> {} ({})".format( e.source - comp_in, e.target - comp_off, str( e ) ) )
                    flowing_sources.add( e.source )

    missing = encountered_sources - flowing_sources
    if( len( missing ) > 0 ):
        print( "{} didn't get any flow".format( sorted( list( missing ) ) ))