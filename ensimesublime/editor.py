import sublime

# from functools import partial as bind


# view names
ENSIME_NOTES_VIEW = "Ensime notes"
ENSIME_OUTPUT_VIEW = "Ensime output"
ENSIME_STACK_VIEW = "Ensime stack"
ENSIME_WATCHES_VIEW = "Ensime watches"

# region names
ENSIME_ERROR_OUTLINE_REGION = "ensime-error"
ENSIME_ERROR_UNDERLINE_REGION = "ensime-error-underline"
ENSIME_BREAKPOINT_REGION = "ensime-breakpoint"
ENSIME_DEBUGFOCUS_REGION = "ensime-debugfocus"
ENSIME_STACKFOCUS_REGION = "ensime-stackfocus"


class Editor(object):
    def __init__(self, window, settings, notes_storage):
        self.w = window
        self.settings = settings
        self.notes_storage = notes_storage

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
        view.erase_regions(ENSIME_ERROR_UNDERLINE_REGION)
        # don't erase breakpoints, they should be permanent regardless of whether ensime is running or not
        # view.erase_regions(ENSIME_BREAKPOINT_REGION)
        view.erase_regions(ENSIME_DEBUGFOCUS_REGION)
        view.erase_regions(ENSIME_STACKFOCUS_REGION)
        # self.redraw_status()

    def uncolorize_all(self):
        for view in self.w.views():
            self.uncolorize(view)

    def redraw_highlights(self, view=None):
        if view is None:
            view = self.w.active_view()
        view.erase_regions(ENSIME_ERROR_OUTLINE_REGION)
        view.erase_regions(ENSIME_ERROR_UNDERLINE_REGION)

        relevant_notes = self.notes_storage.for_file(view.file_name())

        # Underline specific error range
        underlines = [sublime.Region(note.start, note.end) for note in relevant_notes]
        if self.settings.get("error_highlight") and self.settings.get("error_underline"):
            view.add_regions(
                ENSIME_ERROR_UNDERLINE_REGION,
                underlines + view.get_regions(ENSIME_ERROR_UNDERLINE_REGION),
                self.settings.get("error_scope"),
                sublime.DRAW_EMPTY_AS_OVERWRITE)

        # Outline entire errored line
        errors = [view.full_line(note.start) for note in relevant_notes]
        if self.settings.get("error_highlight"):
            view.add_regions(
                ENSIME_ERROR_OUTLINE_REGION,
                errors + view.get_regions(ENSIME_ERROR_OUTLINE_REGION),
                self.settings.get("error_scope"),
                self.settings.get("error_icon"),
                sublime.DRAW_OUTLINED)

        # we might need to add/remove/refresh the error message in the status bar
        # self.redraw_status(view)

        # breakpoints and debug focus should always have priority over red squiggles
        # self.redraw_breakpoints(view)
        # self.redraw_debug_focus(view)
        # self.redraw_stack_focus(view)

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

    def _scroll_viewport(self, v, region):
        # thanks to Fredrik Ehnbom
        # see https://github.com/quarnster/SublimeGDB/blob/master/sublimegdb.py
        # Shouldn't have to call viewport_extent, but it
        # seems to flush whatever value is stale so that
        # the following set_viewport_position works.
        # Keeping it around as a WAR until it's fixed
        # in Sublime Text 2.
        v.viewport_extent()
        # v.set_viewport_position(data, False)
        v.sel().clear()
        v.sel().add(region.begin())
        v.show(region)

    # def redraw_stack_focus(self, view):
    #     view.erase_regions(ENSIME_STACKFOCUS_REGION)
    #     if self.stackframe and view.name() == ENSIME_STACK_VIEW:
    #         focused_region = view.full_line(view.text_point(self.env.stackframe.index, 0))
    #         view.add_regions(
    #             ENSIME_STACKFOCUS_REGION,
    #             [focused_region],
    #             self.settings.get("stackfocus_scope"),
    #             self.settings.get("stackfocus_icon"))
