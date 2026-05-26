"""GwaithStream type definition."""


class GwaithStream:
    def __init__(
        self,
        uid,
        environment,
        name=None,
        decimation=1,
        decimation_offset=0,
        skip_rounds=None,
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
        self.decimation_offset = decimation_offset
        self.skip_rounds = list(skip_rounds or [])
