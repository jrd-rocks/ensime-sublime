class RpcRequest(object):
    def run(self, client_self):
            raise NotImplementedError


class ConnectionInfoRequest(RpcRequest):
    def run(self, client_self):
            client_self.send_request({"typehint": "ConnectionInfoReq"})
