import sublime
import sublime_plugin

from functools import partial as bind

from .paths import relative_path, is_subpath
from . import env


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


class EnsimeCommon(object):
    def __init__(self, owner):
        if type(owner) == sublime.Window:
            self.w = owner
            self.v = None
        elif type(owner) == sublime.View:
            # owner.window() is sometimes None ??
            self.w = owner.window() or sublime.active_window()
            self.v = owner
        else:
            raise Exception("unsupported owner of type: " + str(type(owner)))
        self.env = env.getOrCreateNew(self.w)

    def status_message(self, msg):
        sublime.set_timeout(bind(sublime.status_message, msg), 0)

    def error_message(self, msg):
        sublime.set_timeout(bind(sublime.error_message, msg), 0)

    def is_valid(self):
        return bool(self.env and self.env.valid)

    def is_running(self):
        return self.is_valid() and self.env.running

    def _filename_from_wannabe(self, wannabe):
        if type(wannabe) == type(None):
            v = self.v if hasattr(self, "v") else self.w.active_view()
            return self._filename_from_wannabe(v) if v is not None else None
        if type(wannabe) == sublime.View:
            return wannabe.file_name()
        return wannabe

    def in_project(self, wannabe=None):
        filename = self._filename_from_wannabe(wannabe)
        extension_ok = bool(filename and (filename.endswith("scala") or filename.endswith("java")))
        subpath_ok = bool(self.env and is_subpath(self.env.project_root, filename))
        return extension_ok and subpath_ok

    def project_relative_path(self, wannabe):
        filename = self._filename_from_wannabe(wannabe)
        if not self.in_project(filename):
            return None
        return relative_path(self.env.project_root, filename)

    def _invoke_view_colorer(self, method, *args):
        view = args[0]
        args = args[1:]
        if view == "default":
            view = self.v
        if view is not None:
            colorer = Colorer(view)
            getattr(colorer, method)(*args)

    def _invoke_all_colorers(self, method, *args):
        for i in range(0, self.w.num_groups()):
            if self.w.views_in_group(i):
                v = self.w.active_view_in_group(i)
                colorer = Colorer(v)
                getattr(colorer, method)(*args)

    def colorize(self, view="default"):
        self._invoke_view_colorer("colorize", view)

    def colorize_all(self):
        self._invoke_all_colorers("colorize")

    def uncolorize(self, view="default"):
        self._invoke_view_colorer("uncolorize", view)

    def uncolorize_all(self):
        self._invoke_all_colorers("uncolorize")

    def redraw_highlights(self, view="default"):
        self._invoke_view_colorer("redraw_highlights", view)

    def redraw_all_highlights(self):
        self._invoke_all_colorers("redraw_highlights")

    def redraw_status(self, view="default"):
        self._invoke_view_colorer("redraw_status", view)

    def redraw_breakpoints(self, view="default"):
        self._invoke_view_colorer("redraw_breakpoints", view)

    def redraw_all_breakpoints(self):
        self._invoke_all_colorers("redraw_breakpoints")

    def redraw_debug_focus(self, view="default"):
        self._invoke_view_colorer("redraw_debug_focus", view)

    def redraw_all_debug_focuses(self):
        self._invoke_all_colorers("redraw_debug_focus")

    def redraw_stack_focus(self, view="default"):
        self._invoke_view_colorer("redraw_stack_focus", view)

    def redraw_all_stack_focuses(self):
        self._invoke_all_colorers("redraw_stack_focus")


class EnsimeWindowCommand(EnsimeCommon, sublime_plugin.WindowCommand):
    def __init__(self, window):
        super(EnsimeWindowCommand, self).__init__(window)
        self.window = window


class EnsimeTextCommand(EnsimeCommon, sublime_plugin.TextCommand):
    def __init__(self, owner):
        pass


# class EnsimeEventListener(sublime_plugin.EventListener):
#     def on_load(self, view):
#         if self.is_running() and self.in_project():
#             TypeCheckFileReq(view.file_name()).run(self.env.client)

#     def on_post_save(self, view):
#         pass

#     def on_activated(self, view):
#         pass


class Colorer(EnsimeCommon):
    def colorize(self, view="default"):
        self.uncolorize()
        self.redraw_highlights()
        self.redraw_status()
        self.redraw_breakpoints()
        self.redraw_debug_focus()
        self.redraw_stack_focus()

    def uncolorize(self, view="default"):
        self.v.erase_regions(ENSIME_ERROR_OUTLINE_REGION)
        self.v.erase_regions(ENSIME_ERROR_UNDERLINE_REGION)
        # don't erase breakpoints, they should be permanent regardless of whether ensime is running or not
        # self.v.erase_regions(ENSIME_BREAKPOINT_REGION)
        self.v.erase_regions(ENSIME_DEBUGFOCUS_REGION)
        self.v.erase_regions(ENSIME_STACKFOCUS_REGION)
        self.redraw_status()

    def redraw_highlights(self, view="default"):
        self.v.erase_regions(ENSIME_ERROR_OUTLINE_REGION)
        self.v.erase_regions(ENSIME_ERROR_UNDERLINE_REGION)

        if self.env:
            relevant_notes = self.env.notes_storage.for_file(self.v.file_name())

            # Underline specific error range
            underlines = [sublime.Region(note.start, note.end) for note in relevant_notes]
            if self.env.settings.get("error_highlight") and self.env.settings.get("error_underline"):
                self.v.add_regions(
                    ENSIME_ERROR_UNDERLINE_REGION,
                    underlines + self.v.get_regions(ENSIME_ERROR_UNDERLINE_REGION),
                    self.env.settings.get("error_scope"),
                    sublime.DRAW_EMPTY_AS_OVERWRITE)

            # Outline entire errored line
            errors = [self.v.full_line(note.start) for note in relevant_notes]
            if self.env.settings.get("error_highlight"):
                self.v.add_regions(
                    ENSIME_ERROR_OUTLINE_REGION,
                    errors + self.v.get_regions(ENSIME_ERROR_OUTLINE_REGION),
                    self.env.settings.get("error_scope"),
                    self.env.settings.get("error_icon"),
                    sublime.DRAW_OUTLINED)

            # we might need to add/remove/refresh the error message in the status bar
            self.redraw_status()

            # breakpoints and debug focus should always have priority over red squiggles
            self.redraw_breakpoints()
            self.redraw_debug_focus()
            self.redraw_stack_focus()

    def redraw_status(self, custom_status=None):
        if custom_status:
            self._update_statusbar(custom_status)
        elif self.env and self.env.settings.get("ensime_statusbar_showerrors"):
            if self.v.sel():
                relevant_notes = self.env.notes_storage.for_file(self.v.file_name())
                bol = self.v.line(self.v.sel()[0].begin()).begin()
                eol = self.v.line(self.v.sel()[0].begin()).end()
                msgs = [note.message for note in relevant_notes
                        if (bol <= note.start <= eol) or (bol <= note.end <= eol)]
                self._update_statusbar("; ".join(msgs))
        else:
            self._update_statusbar(None)

    def _update_statusbar(self, status):
        sublime.set_timeout(bind(self._update_statusbar_callback, status), 100)

    def _update_statusbar_callback(self, status):
        settings = self.env.settings if self.env else sublime.load_settings("Ensime.sublime-settings")
        statusgroup = settings.get("ensime_statusbar_group", "ensime")
        status = str(status)
        if settings.get("ensime_statusbar_heartbeat_enabled", True):
            heart_beats = self.is_running()
            if heart_beats:
                def calculate_heartbeat_message():
                    def format_debugging_message(msg):
                        try:
                            return msg % (self.env.profile.name or "")
                        except:
                            return msg

                    if self.in_project():
                        if self.env.profile:
                            return format_debugging_message(
                                settings.get("ensime_statusbar_heartbeat_inproject_debugging"))
                        else:
                            return settings.get("ensime_statusbar_heartbeat_inproject_normal")
                    else:
                        if self.env.profile:
                            return format_debugging_message(
                                settings.get("ensime_statusbar_heartbeat_notinproject_debugging"))
                        else:
                            return settings.get("ensime_statusbar_heartbeat_notinproject_normal")

                heartbeat_message = calculate_heartbeat_message()
                if heartbeat_message:
                    heartbeat_message = heartbeat_message.strip()
                    if not status:
                        status = heartbeat_message
                    else:
                        heartbeat_joint = settings.get("ensime_statusbar_heartbeat_joint")
                        status = heartbeat_message + heartbeat_joint + status
        if status:
            maxlength = settings.get("ensime_statusbar_maxlength", 150)
            if len(status) > maxlength:
                status = status[0:maxlength] + "..."
            self.v.set_status(statusgroup, status)
        else:
            self.v.erase_status(statusgroup)

    def redraw_breakpoints(self):
        self.v.erase_regions(ENSIME_BREAKPOINT_REGION)
        if self.v.is_loading():
            sublime.set_timeout(self.redraw_breakpoints, 100)
        else:
            if self.env:
                relevant_breakpoints = [breakpoint for breakpoint in self.env.breakpoints if same_paths(
                    breakpoint.file_name, self.v.file_name())]
                regions = [self.v.full_line(self.v.text_point(breakpoint.line - 1, 0))
                           for breakpoint in relevant_breakpoints]
                self.v.add_regions(
                    ENSIME_BREAKPOINT_REGION,
                    regions,
                    self.env.settings.get("breakpoint_scope"),
                    self.env.settings.get("breakpoint_icon"),
                    sublime.HIDDEN)
                # sublime.DRAW_OUTLINED)

    def redraw_debug_focus(self):
        self.v.erase_regions(ENSIME_DEBUGFOCUS_REGION)
        if self.v.is_loading():
            sublime.set_timeout(self.redraw_debug_focus, 100)
        else:
            if self.env and self.env.focus and same_paths(self.env.focus.file_name, self.v.file_name()):
                focused_region = self.v.full_line(self.v.text_point(self.env.focus.line - 1, 0))
                self.v.add_regions(
                    ENSIME_DEBUGFOCUS_REGION,
                    [focused_region],
                    self.env.settings.get("debugfocus_scope"),
                    self.env.settings.get("debugfocus_icon"))
                w = self.v.window() or sublime.active_window()
                w.focus_view(self.v)
                self.redraw_breakpoints()
                sublime.set_timeout(bind(self._scroll_viewport, self.v, focused_region), 0)

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

    def redraw_stack_focus(self):
        self.v.erase_regions(ENSIME_STACKFOCUS_REGION)
        if self.env and self.env.stackframe and self.v.name() == ENSIME_STACK_VIEW:
            focused_region = self.v.full_line(self.v.text_point(self.env.stackframe.index, 0))
            self.v.add_regions(
                ENSIME_STACKFOCUS_REGION,
                [focused_region],
                self.env.settings.get("stackfocus_scope"),
                self.env.settings.get("stackfocus_icon"))
