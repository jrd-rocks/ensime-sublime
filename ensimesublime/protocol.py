# coding: utf-8
import sublime

from functools import partial as bind

from util import catch, Pretty
from notes import Note
from outgoing import AddImportRefactorDesc, TypeCheckFilesReq
from patch import fromfile
from config import feedback
from symbol_format import completion_to_suggest


class ProtocolHandler(object):
    """Mixin for common behavior of handling ENSIME protocol responses.

    Actual handler implementations are abstract and should be implemented by a
    subclass. Requires facilities of an ``EnsimeClient``.
    """

    def __init__(self):
        self.server_version = "unknown"
        self.handlers = {}
        self.register_responses_handlers()

    def register_responses_handlers(self):
        """Register handlers for responses from the server.

        A handler must accept only one parameter: `payload`.
        """
        self.handlers["ConnectionInfo"] = self.handle_connection_info
        self.handlers["SendBackgroundMessageEvent"] = self.handle_background_message
        self.handlers["SymbolInfo"] = self.handle_symbol_info
        self.handlers["IndexerReadyEvent"] = self.handle_indexer_ready
        self.handlers["AnalyzerReadyEvent"] = self.handle_analyzer_ready
        self.handlers["NewScalaNotesEvent"] = self.handle_scala_notes
        self.handlers["NewJavaNotesEvent"] = self.handle_java_notes
        self.handlers["ClearAllScalaNotesEvent"] = self.handle_clear_scala_notes
        # self.handlers["BasicTypeInfo"] = self.show_type
        # self.handlers["ArrowTypeInfo"] = self.show_type
        self.handlers["FullTypeCheckCompleteEvent"] = self.handle_typecheck_complete
        # self.handlers["StringResponse"] = self.handle_string_response
        self.handlers["CompletionInfoList"] = self.handle_completion_info_list
        # self.handlers["SymbolSearchResults"] = self.handle_symbol_search
        # self.handlers["DebugOutputEvent"] = self.handle_debug_output
        # self.handlers["DebugBreakEvent"] = self.handle_debug_break
        # self.handlers["DebugBacktrace"] = self.handle_debug_backtrace
        # self.handlers["DebugVmError"] = self.handle_debug_vm_error
        self.handlers["RefactorDiffEffect"] = self.apply_refactor
        self.handlers["ImportSuggestions"] = self.handle_import_suggestions
        # self.handlers["PackageInfo"] = self.handle_package_info

    def handle_incoming_response(self, call_id, payload):
        """Get a registered handler for a given response and execute it."""
        self.env.logger.debug('handle_incoming_response: in [typehint: %s, call ID: %s]',
                              payload['typehint'], call_id)  # We already log the full JSON response

        typehint = payload["typehint"]
        handler = self.handlers.get(typehint)

        def feature_not_supported(m):
            msg = feedback["handler_not_implemented"]
            self.env.logger.error(msg.format(typehint, self.server_version))
            self.env.status_message(msg.format(typehint, self.server_version))

        if handler:
            with catch(NotImplementedError, feature_not_supported):
                handler(call_id, payload)
        else:
            self.env.logger.warning('Response has not been handled: %s', Pretty(payload))

    def handle_connection_info(self, call_id, payload):
        self.server_version = payload.get("version", "unknown")

    def handle_background_message(self, call_id, payload):
        self.env.logger.info("{} : {}"
                             .format(payload.get("code", "unknown code"),
                                     payload.get("detail", "no detail")))

    def handle_indexer_ready(self, call_id, payload):
        self.env.logger.info("Indexer is ready.")

    def handle_analyzer_ready(self, call_id, payload):
        self.env.logger.info("Analyzer is ready.")
        files = []
        for view in self.env.window.views():
            files.append(view.file_name())
        TypeCheckFilesReq(files).run_in(self.env, async=True)
        self.env.editor.show_errors = True

    def handle_scala_notes(self, call_id, payload):
        self.env.notes_storage.append(map(Note, payload['notes']))

    def handle_java_notes(self, call_id, payload):
        pass

    def handle_clear_scala_notes(self, call_id, payload):
        self.env.notes_storage.clear()

    def handle_typecheck_complete(self, call_id, payload):
        self.env.editor.redraw_all_highlights()
        self.env.logger.info("Handled FullTypecheckCompleteEvent. Redrawing highlights.")

    def handle_debug_vm_error(self, call_id, payload):
        raise NotImplementedError()

    def handle_import_suggestions(self, call_id, payload):
        imports = list()
        for suggestions in payload['symLists']:
            for suggestion in suggestions:
                imports.append(suggestion['name'].replace('$', '.'))
        imports = list(sorted(set(imports)))

        if not imports:
            self.env.error_message('No import suggestions found.')
            return

        def do_refactor(choice):
            if choice > -1:
                file_name = self.call_options[call_id].get('file_name')
                # request is async, file is reverted when patch is received and applied
                AddImportRefactorDesc(file_name, imports[choice]).run_in(self.env, async=True)

        sublime.set_timeout(bind(self.env.window.show_quick_panel, imports, do_refactor), 0)

    def handle_package_info(self, call_id, payload):
        raise NotImplementedError()

    def handle_symbol_search(self, call_id, payload):
        raise NotImplementedError()

    def handle_symbol_info(self, call_id, payload):
        decl_pos = payload.get("declPos")
        if decl_pos is None:
            self.env.error_message("Couldn't find the declaration position for symbol.\n{}"
                                   .format(payload.get("name")))
            return
        f = decl_pos.get("file")
        if f is None:
            self.env.error_message("Couldn't find the file where it's defined.")
            return
        self.env.logger.debug("Jumping to file : {}".format(f))
        view = self.env.window.open_file(f)

        # either has line or offset
        def _scroll_once_loaded(attempts=10):
            offset = decl_pos.get("offset")
            line = decl_pos.get("line")
            if not offset and not line:
                self.env.logger.debug("No offset or line number were found.")
                return
            while view.is_loading() and attempts:
                sublime.set_timeout(_scroll_once_loaded, 100)
                attempts -= 1
            if not view.is_loading():
                if not offset:
                    offset = view.text_point(line + 1, 1)
                self.env.logger.debug("Scrolling to offset : {}".format(offset))
                view.show_at_center(offset)
            else:
                self.env.logger.debug("Scrolling failed as the view wasn't ready.")

        sublime.set_timeout(_scroll_once_loaded, 0)

    def handle_string_response(self, call_id, payload):
        raise NotImplementedError()

    def handle_completion_info_list(self, call_id, payload):
        """Handler for a completion response."""
        self.env.logger.debug('handle_completion_info_list: in')
        # filter out completions without `typeInfo` field to avoid server bug. See #324
        completions = [c for c in payload["completions"] if "typeInfo" in c]
        self.env.editor.suggestions = [completion_to_suggest(c) for c in completions]
        self.env.logger.debug('handle_completion_info_list: {}'
                              .format(Pretty(self.env.editor.suggestions)))

    def handle_type_inspect(self, call_id, payload):
        raise NotImplementedError()

    def apply_refactor(self, call_id, payload):
        supported_refactorings = ["AddImport", "OrganizeImports", "Rename", "InlineLocal"]
        if payload["refactorType"]["typehint"] in supported_refactorings:
            diff_file = payload["diff"]
            patch_set = fromfile(diff_file)
        if not patch_set:
            self.env.logger.warning("Couldn't parse diff_file: {}"
                                    .format(diff_file))
            return
        result = patch_set.apply(0, "/")
        if result:
            file = self.refactorings[payload['procedureId']]
            sublime.set_timeout(bind(self.env.editor.reload_file, self.env.window.find_open_file(file)), 0)
            self.env.logger.info("Refactoring succeeded, patch file: {}"
                                 .format(diff_file))
            self.env.status_message("Refactoring succeeded")
        else:
            self.env.logger.error("Patch refactoring failed, patch file: {}"
                                  .format(diff_file))
            self.env.status_message("Refactor failed: {}".format(diff_file))

    def show_type(self, call_id, payload):
        raise NotImplementedError()
