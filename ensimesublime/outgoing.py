class RpcRequest(object):
    def run_in(self, env):
        raise NotImplementedError


class ConnectionInfoRequest(RpcRequest):
    def run_in(self, env):
        call_id = env.client.send_request({"typehint": "ConnectionInfoReq"})
        return call_id


class TypeCheckFilesReq(RpcRequest):
    def __init__(self, filenames):
        self.filenames = list(filenames)

    def run_in(self, env):
        env.notes_storage.filter_files(self.filenames)
        call_id = env.client.send_request(
            {"typehint": "TypecheckFilesReq",
             "files": self.filenames})
        return call_id
