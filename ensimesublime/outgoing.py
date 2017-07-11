import json


class RpcRequest(object):

    def send_request(self, request, client, async):
        """Send a request to the server."""
        client.env.logger.debug('send_request: in')

        message = {'callId': client.call_id, 'req': request}
        client.call_options[client.call_id] = {'async': async}
        client.call_options[client.call_id].update(self.call_options())
        client.env.logger.info('send_request: %s', message)
        client.send(json.dumps(message))

        call_id = client.call_id
        client.call_id += 1
        return call_id

    def run_in(self, env, async=False):
        call_id = self.send_request(self.json_repr(), env.client, async)
        if not async:
            got_response = env.client.get_response(call_id)
            return got_response
        return True

    def json_repr(self):
        raise NotImplementedError

    def call_options(self):
        return {}


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
                "maxResults": self.max_results,
                "names": self.names,
                "typehint": "ImportSuggestionsReq",
                "file": self.file}

    def call_options(self):
        return {'file_name': self.file}


class RefactorRequest(RpcRequest):
    def __init__(self):
        super(RefactorRequest, self).__init__()

    def run_in(self, env, async=False):
        call_id = self.send_refactor_request(self.json_repr(), env.client, async)
        if not async:
            got_response = env.client.get_response(call_id)
            return got_response
        return True

    def send_refactor_request(self, req, client, async):
        """Send a refactor request to the Ensime server.

        The `ref_params` field will always have a field `type`.
        """
        ref_type = req['ref_type']
        ref_params = req['ref_params']
        ref_options = req['ref_options']
        request = {
            "typehint": ref_type,
            "procId": client.refactor_id,
            "params": ref_params
        }
        f = ref_params["file"]
        client.refactorings[client.refactor_id] = f
        client.refactor_id += 1
        request.update(ref_options)
        return self.send_request(request, client, async)


class AddImportRefactorDesc(RefactorRequest):
    def __init__(self, file, name):
        super(AddImportRefactorDesc, self).__init__()
        self.file = file
        self.name = name

    def json_repr(self):
        return {"ref_type": "RefactorReq",
                "ref_params": {"typehint": "AddImportRefactorDesc",
                               "file": self.file,
                               "qualifiedName": self.name},
                "ref_options": {"interactive": False}}


class OrganiseImports(RefactorRequest):
    def __init__(self, file):
        super(OrganiseImports, self).__init__()
        self.file = file

    def json_repr(self):
        return {"ref_type": "RefactorReq",
                "ref_params": {"typehint": "OrganiseImportsRefactorDesc",
                               "file": self.file,
                               },
                "ref_options": {"interactive": False}}


class RenameRefactorDesc(RefactorRequest):
    def __init__(self, new_name, start, end, file):
        super(RenameRefactorDesc, self).__init__()
        self.new_name = new_name
        self.start = start
        self.end = end
        self.file = file

    def json_repr(self):
        return {"ref_type": "RefactorReq",
                "ref_params": {"typehint": "RenameRefactorDesc",
                               "newName": self.new_name,
                               "start": self.start,
                               "end": self.end,
                               "file": self.file,
                               },
                "ref_options": {"interactive": False}}


class InlineLocalRefactorDesc(RefactorRequest):
    def __init__(self, start, end, file):
        super(InlineLocalRefactorDesc, self).__init__()
        self.start = start
        self.end = end
        self.file = file

    def json_repr(self):
        return {"ref_type": "RefactorReq",
                "ref_params": {"typehint": "InlineLocalRefactorDesc",
                               "start": self.start,
                               "end": self.end,
                               "file": self.file,
                               },
                "ref_options": {"interactive": False}}
