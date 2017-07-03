class RpcRequest(object):
    def run(self, client_self):
        raise NotImplementedError


class ConnectionInfoRequest(RpcRequest):
    def run(self, client_self):
        client_self.send_request({"typehint": "ConnectionInfoReq"})


class TypeCheckFileReq(RpcRequest):
    def __init__(self, filename):
        self.filename = filename

    def run(self, client):
        client.send_request(
            {"typehint": "TypecheckFilesReq",
             "files": [self.filename]})
