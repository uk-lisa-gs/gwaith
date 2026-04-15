class GwaithFile:
    def __init__(self, uid, path, final_path, produced_by=None, retention_level=None):
        # This is the unique identifier by which we will refer to the file
        # from other nodes etc.
        self.uid = uid
        # The local path that the file will be saved in until it has been
        # used for the final time
        self.path = path
        # The file path that it will be moved to after it is no longer needed
        self.final_path = final_path
        # a retention level to indicate to compare to a global level to see
        # if the file will just b e deleted after it has been used
        self.retention_level = retention_level
        # The UID of the node that created the file
        self.produced_by = produced_by
        # The UIDs of node that will use the file down the line
        self.used_by = []

class GwaithNode:
    def __init__(
        self,
        uid,
        round_index=None,
        stream_uid=None,
    ):
        # This is the unique identifier by which we will refer to the node
        # from the files which it produces etc.
        self.uid = uid
        # The command that is being run by ths node
        self.command = []
        # Keeping track of which round this node belongs to
        self.round_index = round_index
        # the id of the stream that the node is within 
        self.stream = stream_uid
        # The list of files that are needed as input to the node
        self.uses = []
        # The list of files that the node will produce
        self.produces = []

class GwaithStream:
    def __init__(
        self,
        uid, 
        environment,
        name=None,
        decimation=1,
        skip_rounds=[]
    ):
        # Unique identifier for the stream
        self.uid = uid
        # Human-readable name for the stream
        self.name = name
        # List of node UIDs belonging to this stream
        self.nodes = []
        # The environment that this stream runs the nodes in
        self.environment = environment
        self.decimation = decimation
        self.skip_rounds = skip_rounds


