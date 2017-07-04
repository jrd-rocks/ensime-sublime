from .paths import is_subpath


class RpcRequest(object):
    def run_in(self, env):
        raise NotImplementedError


class ConnectionInfoRequest(RpcRequest):
    def run_in(self, env):
        call_id = env.client.send_request({"typehint": "ConnectionInfoReq"})
        return call_id


class TypeCheckFileReq(RpcRequest):
    def __init__(self, filename):
        self.filename = filename

    def run_in(self, env):
        # env.notes_storage.filter_files(self.filenames)
        src_root = None
        for src in env.grouped_srcs.keys():
            if is_subpath(src, self.filename):
                src_root = src  # F841
                break
        if src_root is not None:
            srcs = env.grouped_srcs['src_root']
            env.logger.debug("Cleared scala notes of files in any of {s}".format(s=srcs))
            env.notes_storage.filter_files(lambda f: any(is_subpath(src, f) for src in srcs))
        call_id = env.client.send_request(
            {"typehint": "TypecheckFilesReq",
             "files": [self.filename]})
        return call_id
