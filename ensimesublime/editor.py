import sublime

import html


# view names
ENSIME_NOTES_VIEW = "Ensime notes"
ENSIME_OUTPUT_VIEW = "Ensime output"
ENSIME_STACK_VIEW = "Ensime stack"
ENSIME_WATCHES_VIEW = "Ensime watches"

# region names
ENSIME_ERROR_OUTLINE_REGION = "ensime-error"
ENSIME_WARNING_OUTLINE_REGION = "ensime-warning"
ENSIME_BREAKPOINT_REGION = "ensime-breakpoint"
ENSIME_DEBUGFOCUS_REGION = "ensime-debugfocus"
ENSIME_STACKFOCUS_REGION = "ensime-stackfocus"


class Editor(object):
    def __init__(self, window, settings, notes_storage):
        self.w = window
        self.settings = settings
        self.notes_storage = notes_storage
        self.phantom_sets_by_buffer = {}
        self.show_errors = False

    def colorize(self, view=None):
        if view is None:
            view = self.w.active_view()
        self.uncolorize(view)
        self.redraw_highlights(view)
        # self.redraw_status()
        # self.redraw_breakpoints()
        # self.redraw_debug_focus()
        # self.redraw_stack_focus()

    def uncolorize(self, view=None):
        if view is None:
            view = self.w.active_view()
        view.erase_regions(ENSIME_ERROR_OUTLINE_REGION)
        view.erase_regions(ENSIME_WARNING_OUTLINE_REGION)
        # don't erase breakpoints, they should be permanent regardless of whether ensime is running or not
        # view.erase_regions(ENSIME_BREAKPOINT_REGION)
        # view.erase_regions(ENSIME_DEBUGFOCUS_REGION)
        # view.erase_regions(ENSIME_STACKFOCUS_REGION)
        # self.redraw_status()

    def uncolorize_all(self):
        for view in self.w.views():
            self.uncolorize(view)

    def redraw_all_highlights(self):
        for view in self.w.views():
            self.redraw_highlights(view)
        if(self.show_errors):
            self.update_phantoms()

    def redraw_highlights(self, view=None):
        if view is None:
            view = self.w.active_view()
        view.erase_regions(ENSIME_ERROR_OUTLINE_REGION)
        view.erase_regions(ENSIME_WARNING_OUTLINE_REGION)

        relevant_notes = self.notes_storage.for_file(view.file_name())

        # stippled underline the warnings
        warnings = [view.full_line(note.start) for note in relevant_notes if note.severity == "NoteWarn"]
        if self.settings.get("warning_highlight"):
            view.add_regions(
                ENSIME_WARNING_OUTLINE_REGION,
                warnings + view.get_regions(ENSIME_WARNING_OUTLINE_REGION),
                self.settings.get("warning_scope"),
                self.settings.get("warning_icon"),
                sublime.DRAW_NO_FILL)
        # Outline entire errored line
        errors = [view.full_line(note.start) for note in relevant_notes if note.severity == "NoteError"]
        if self.settings.get("error_highlight"):
            view.add_regions(
                ENSIME_ERROR_OUTLINE_REGION,
                errors + view.get_regions(ENSIME_ERROR_OUTLINE_REGION),
                self.settings.get("error_scope"),
                self.settings.get("error_icon"),
                sublime.DRAW_NO_FILL)

        # we might need to add/remove/refresh the error message in the status bar
        # self.redraw_status(view)
        # self.update_phantoms(view)
        # breakpoints and debug focus should always have priority over red squiggles
        # self.redraw_breakpoints(view)
        # self.redraw_debug_focus(view)
        # self.redraw_stack_focus(view)

    def update_phantoms(self):
        stylesheet = '''
            <style>
                .warn{
                    background-color: color(var(--background) blend(yellow 50%));
                }
                div.error, div.warn {
                    padding: 0.4rem 0 0.4rem 0.7rem;
                    margin: 0.2rem 0;
                    border-radius: 2px;
                }
                div.error span.message, div.warn span.message {
                    padding-right: 0.7rem;
                }
                div.error a, div.warn a {
                    text-decoration: inherit;
                    padding: 0.35rem 0.7rem 0.45rem 0.8rem;
                    position: relative;
                    bottom: 0.05rem;
                    border-radius: 0 2px 2px 0;
                    font-weight: bold;
                }
                html.dark div.error a, html.dark div.warn a {
                    background-color: #00000018;
                }
                html.light div.error a, html.light div.warn a {
                    background-color: #ffffff18;
                }
            </style>
        '''
        for file in self.notes_storage.per_file_cache.keys():
            view = self.w.find_open_file(str(file))
            buffer_id = view.buffer_id()
            if buffer_id not in self.phantom_sets_by_buffer:
                phantom_set = sublime.PhantomSet(view, "exec")
                self.phantom_sets_by_buffer[buffer_id] = phantom_set
            else:
                phantom_set = self.phantom_sets_by_buffer[buffer_id]

            phantoms = []

            errs = self.notes_storage.for_file(view.file_name())

            for note in errs:
                if note.severity == "NoteInfo":
                    continue
                clss = "error" if note.severity == "NoteError" else "warn"
                phantoms.append(sublime.Phantom(
                    sublime.Region(note.start, note.end),
                    ('<body id=inline-error>' + stylesheet +
                        '<div class=' + clss + '>' +
                        '<span class="message">' + html.escape(note.message, quote=False) + '</span>' +
                        '<a href=hide>' + chr(0x00D7) + '</a></div>' +
                        '</body>'),
                    sublime.LAYOUT_BLOCK,
                    on_navigate=self.on_phantom_navigate))

            phantom_set.update(phantoms)

    def hide_phantoms(self):
        for file in self.notes_storage.per_file_cache.keys():
            view = self.w.find_open_file(str(file))
            view.erase_phantoms("exec")
        self.show_errors = False
        self.phantom_sets_by_buffer = {}

    def on_phantom_navigate(self, url):
        self.hide_phantoms()

    def reload_file(self, view=None):
        if view:
            original_size = view.size()
            original_pos = view.sel()[0].begin()
            # Load changes
            view.run_command("revert")

            # Wait until view loaded then move cursor to original position
            def on_load():
                if view.is_loading():
                    # Wait again
                    sublime.set_timeout(on_load, 50)
                else:
                    size_diff = view.size() - original_size
                    new_pos = original_pos + size_diff
                    view.sel().clear()
                    view.sel().add(sublime.Region(new_pos))
                    view.show(new_pos)
                    view.run_command("save")

            on_load()

    # def redraw_status(self, view, custom_status=None):
    #     if custom_status:
    #         self._update_statusbar(custom_status)
    #     elif self.settings.get("ensime_statusbar_showerrors"):
    #         if view.sel():
    #             relevant_notes = self.notes_storage.for_file(view.file_name())
    #             bol = view.line(view.sel()[0].begin()).begin()
    #             eol = view.line(view.sel()[0].begin()).end()
    #             msgs = [note.message for note in relevant_notes
    #                     if (bol <= note.start <= eol) or (bol <= note.end <= eol)]
    #             self._update_statusbar("; ".join(msgs))
    #     else:
    #         self._update_statusbar(None)

    # def _update_statusbar(self, status):
    #     sublime.set_timeout(bind(self._update_statusbar_callback, status), 100)

    # def _update_statusbar_callback(self, status):
    #     settings = self.settings
    #     statusgroup = settings.get("ensime_statusbar_group", "ensime")
    #     status = str(status)
    #     if settings.get("ensime_statusbar_heartbeat_enabled", True):
    #         heart_beats = True  # TODO. figure out
    #         if heart_beats:
    #             def calculate_heartbeat_message():
    #                 def format_debugging_message(msg):
    #                     try:
    #                         return msg % (self.env.profile.name or "")
    #                     except:
    #                         return msg

    #                 if self.in_project():
    #                     if self.env.profile:
    #                         return format_debugging_message(
    #                             settings.get("ensime_statusbar_heartbeat_inproject_debugging"))
    #                     else:
    #                         return settings.get("ensime_statusbar_heartbeat_inproject_normal")
    #                 else:
    #                     if self.env.profile:
    #                         return format_debugging_message(
    #                             settings.get("ensime_statusbar_heartbeat_notinproject_debugging"))
    #                     else:
    #                         return settings.get("ensime_statusbar_heartbeat_notinproject_normal")

    #             heartbeat_message = calculate_heartbeat_message()
    #             if heartbeat_message:
    #                 heartbeat_message = heartbeat_message.strip()
    #                 if not status:
    #                     status = heartbeat_message
    #                 else:
    #                     heartbeat_joint = settings.get("ensime_statusbar_heartbeat_joint")
    #                     status = heartbeat_message + heartbeat_joint + status
    #     if status:
    #         maxlength = settings.get("ensime_statusbar_maxlength", 150)
    #         if len(status) > maxlength:
    #             status = status[0:maxlength] + "..."
    #         view.set_status(statusgroup, status)
    #     else:
    #         view.erase_status(statusgroup)

    # def redraw_breakpoints(self, view):
    #     view.erase_regions(ENSIME_BREAKPOINT_REGION)
    #     if view.is_loading():
    #         sublime.set_timeout(self.redraw_breakpoints, 100)
    #     else:
    #         if self.env:
    #             relevant_breakpoints = [breakpoint for breakpoint in self.env.breakpoints if same_paths(
    #                 breakpoint.file_name, view.file_name())]
    #             regions = [view.full_line(view.text_point(breakpoint.line - 1, 0))
    #                        for breakpoint in relevant_breakpoints]
    #             view.add_regions(
    #                 ENSIME_BREAKPOINT_REGION,
    #                 regions,
    #                 self.env.settings.get("breakpoint_scope"),
    #                 self.env.settings.get("breakpoint_icon"),
    #                 sublime.HIDDEN)
    #             # sublime.DRAW_OUTLINED)

    # def redraw_debug_focus(self, view):
    #     view.erase_regions(ENSIME_DEBUGFOCUS_REGION)
    #     if view.is_loading():
    #         sublime.set_timeout(self.redraw_debug_focus, 100)
    #     else:
    #         if self.env and self.env.focus and same_paths(self.env.focus.file_name, view.file_name()):
    #             focused_region = view.full_line(view.text_point(self.env.focus.line - 1, 0))
    #             view.add_regions(
    #                 ENSIME_DEBUGFOCUS_REGION,
    #                 [focused_region],
    #                 self.env.settings.get("debugfocus_scope"),
    #                 self.env.settings.get("debugfocus_icon"))
    #             w = view.window() or sublime.active_window()
    #             w.focus_view(view)
    #             self.redraw_breakpoints()
    #             sublime.set_timeout(bind(self._scroll_viewport, view, focused_region), 0)

    # def _scroll_viewport(self, v, region):
    #     # thanks to Fredrik Ehnbom
    #     # see https://github.com/quarnster/SublimeGDB/blob/master/sublimegdb.py
    #     # Shouldn't have to call viewport_extent, but it
    #     # seems to flush whatever value is stale so that
    #     # the following set_viewport_position works.
    #     # Keeping it around as a WAR until it's fixed
    #     # in Sublime Text 2.
    #     v.viewport_extent()
    #     # v.set_viewport_position(data, False)
    #     v.sel().clear()
    #     v.sel().add(region.begin())
    #     v.show(region)

    # def redraw_stack_focus(self, view):
    #     view.erase_regions(ENSIME_STACKFOCUS_REGION)
    #     if self.stackframe and view.name() == ENSIME_STACK_VIEW:
    #         focused_region = view.full_line(view.text_point(self.env.stackframe.index, 0))
    #         view.add_regions(
    #             ENSIME_STACKFOCUS_REGION,
    #             [focused_region],
    #             self.settings.get("stackfocus_scope"),
    #             self.settings.get("stackfocus_icon"))
