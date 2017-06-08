

class HaProxyConnectionRefused(Exception):
    """This exception indicates that the haproxy stats socked connection was
    refused.
    """

    def __init__(self, exception):
        super(HaProxyConnectionRefused, self).__init__(*exception.args)
