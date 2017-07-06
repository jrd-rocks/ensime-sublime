import json


class RpcRequest(object):

    def send_request(self, request, client, async):
        """Send a request to the server."""
        client.env.logger.debug('send_request: in')

        message = {'callId': client.call_id, 'req': request}
        client.call_options[client.call_id] = {'async': async}
        client.call_options[client.call_id].update(self.call_options())
        client.env.logger.debug('send_request: %s', message)
        client.send(json.dumps(message))

        call_id = client.call_id
        client.call_id += 1
        return call_id

    def run_in(self, env, async=False):
        self.send_request(self.json_repr(), env.client, async)

    def json_repr(self):
        raise NotImplementedError

    def call_options(self):
        return None


class ConnectionInfoRequest(RpcRequest):
    def __init__(self):
        super(ConnectionInfoRequest, self).__init__()

    def json_repr(self):
        return {"typehint": "ConnectionInfoReq"}


class TypeCheckFilesReq(RpcRequest):
    def __init__(self, filenames):
        super(TypeCheckFilesReq, self).__init__()
        self.filenames = list(filenames)

    def json_repr(self):
        return {"typehint": "TypecheckFilesReq",
                "files": self.filenames}


class SymbolAtPointReq(RpcRequest):
    def __init__(self, filename, pos):
        super(SymbolAtPointReq, self).__init__()
        self.filename = filename
        self.pos = pos

    def json_repr(self):
        return {"point": self.pos,
                "typehint": "SymbolAtPointReq",
                "file": self.filename}


class ImportSuggestionsReq(RpcRequest):
    def __init__(self, pos, file, word, max_results=10):
        super(ImportSuggestionsReq, self).__init__()
        self.pos = pos
        self.file = file
        self.names = [word]
        self.max_results = max_results

    def json_repr(self):
        return {"point": self.pos,
                "maxResults": self.maxResults,
                "names": self.names,
                "typehint": "ImportSuggestionsReq",
                "file": self.file}
