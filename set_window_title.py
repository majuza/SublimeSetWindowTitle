import sublime

import os
import time
from sublime_plugin import EventListener

WAS_DIRTY = "set_window_title_was_dirty"


class SetWindowTitle(EventListener):

  script_path = None

  def __init__(self):
    sublime.set_timeout_async(self.on_sublime_started, 1000)

  def on_sublime_started(self):
    packages_path = sublime.packages_path()
    while not packages_path:
      packages_path = sublime.packages_path()
      time.sleep(1)

    self.script_path = os.path.join(
        packages_path, __package__, "fix_window_title.sh")

    for window in sublime.windows():
      self.run(window.active_view())

  def on_activated_async(self, view):
    self.run(view)

  def on_modified_async(self, view):
    if view.settings().get(WAS_DIRTY, None) != view.is_dirty():
      self.run(view)

  def on_post_save_async(self, view):
    self.run(view)

  def run(self, view):
    if not self.script_path:
      print("[SetWindowTitle] Info: ST haven't finished loading yet, skipping.")
      return

    view_name = view.name() or view.file_name()
    project = self.get_project(view)

    official_title = self.get_official_title(view, view_name, project)
    new_title = self.get_new_title(view, view_name, project)
    self.rename_window(official_title, new_title)
    view.settings().set(WAS_DIRTY, view.is_dirty())

  def get_project(self, view):
    project = None
    window = view.window()
    if not window:
      return

    project = window.project_file_name()
    if not project:
      folders = window.folders()
      project = folders[0] if folders else ""
    if project:
      project = os.path.basename(project)
      project = os.path.splitext(project)[0]

    return project

  def get_official_title(self, view, view_name, project):
    """Returns the official name for a given view.

    Note: The full file path isn't computed,
    because ST uses `~` to shorten the path.
    """
    official_title = os.path.basename(view_name) if view_name else "untitled"
    if view.is_dirty():
      official_title += " •"
    if project:
      official_title += " (%s)" % project
    official_title += " - Sublime Text"
    return official_title

  def get_new_title(self, view, view_name, project, old_title):
    """Returns the new name for a view, according to the user preferences."""
    settings = sublime.load_settings("set_window_title.sublime-settings")

    full_path = view_name or settings.get('untitled')
    rel_path = full_path

    # Don't try to compute relative path if we don't have a file path.
    if view.file_name():
      full_path = view.file_name()
      window = view.window()
      folders = window.folders() if window else None
      root = folders[0] if folders else None
      if root:
        rel_path = os.path.relpath(view.file_name(), root)

    template = settings.get("template")
    template = self._replace_condition(
        template, "has_project", project, settings)
    template = self._replace_condition(
        template, "is_dirty", view.is_dirty(), settings)

    return template.format(
        rel_path=rel_path, full_path=full_path, project=project)

  def _replace_condition(self, template, condition, value, settings):
    if value:
      replacement = settings.get(condition + "_true")
    else:
      replacement = settings.get(condition + "_false")
    return template.replace("{%s}" % condition, replacement)

  def rename_window(self, official_title, new_title):
    """Rename a subl window using the fix_window_title.sh script."""
    settings = sublime.load_settings("set_window_title.sublime-settings")
    debug = settings.get("debug")
    cmd = 'bash %s "%s" "%s"' % (self.script_path, official_title, new_title)
    if debug:
      print("[SetWindowTitle] Debug: running: ", cmd)
    output = os.popen(cmd + " 1&2").read()
    if debug:
      print("[SetWindowTitle] Debug: result: ", output)
