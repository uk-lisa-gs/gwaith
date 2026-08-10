"""GwaithNode type definition."""


class GwaithNode:
    def __init__(
        self,
        uid,
        round_index=None,
        stream_uid=None,
        name=None,
        resources=None,
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
        # Human readable name
        self.name = name or uid
        # Resource requirements for the node
        self.resources = resources or {}
        # The list of files that are needed as input to the node
        self.uses = []
        # The list of files that the node will produce
        self.produces = []
