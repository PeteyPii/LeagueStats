from lol import common_flag
from lol.command import Flag


class RegionFlag(common_flag.CommonFlag):

    def __init__(self, command):
        super().__init__(Flag(name="region", default="NA", description="Region to use for API calls."), command)
