"""."""

import re
from typing import Union, Dict, Type

from gdb.common import Common


class App(Common):
    """Main application class."""

    def __init__(self, common, backendStr: str, proxyCmd: str,
                 clientCmd: str):
        """ctor."""
        super().__init__(common)
        self._last_command: Union[str, None] = None

        self.vim.exec_lua(f"nvimgdb.new('{backendStr}', '{proxyCmd}', '{clientCmd}')")

    def breakpoint_clear_all(self):
        """Clear all breakpoints."""
        if self.vim.exec_lua("return nvimgdb.i().parser:is_running()"):
            # pause first
            self.vim.exec_lua("nvimgdb.i().client:interrupt()")
        # The breakpoint signs will be requeried later automatically
        self.vim.exec_lua("nvimgdb.i():send('delete_breakpoints')")

    def on_tab_enter(self):
        """Actions to execute when a tabpage is entered."""
        # Restore the signs as they may have been spoiled
        if self.vim.exec_lua("return nvimgdb.i().parser:is_paused()"):
            self.vim.exec_lua("nvimgdb.i().cursor:show()")
        # Ensure breakpoints are shown if are queried dynamically
        self.vim.exec_lua("nvimgdb.i().win:query_breakpoints()")

    def on_tab_leave(self):
        """Actions to execute when a tabpage is left."""
        # Hide the signs
        self.vim.exec_lua("nvimgdb.i().cursor:hide()")
        self.vim.exec_lua("nvimgdb.i().breakpoint:clear_signs()")

    def on_buf_enter(self):
        """Actions to execute when a buffer is entered."""
        # Apply keymaps to the jump window only.
        if self.vim.current.buffer.options['buftype'] != 'terminal' \
                and self.vim.exec_lua("return nvimgdb.i().win:is_jump_window_active()"):
            # Make sure the cursor stay visible at all times

            scroll_off = self.vim.exec_lua("return nvimgdb.i().config:get('set_scroll_off')")
            if scroll_off is not None:
                self.vim.command("if !&scrolloff"
                                 f" | setlocal scrolloff={str(scroll_off)}"
                                 " | endif")
            self.vim.exec_lua("nvimgdb.i().keymaps:dispatch_set()")
            # Ensure breakpoints are shown if are queried dynamically
            self.vim.exec_lua("nvimgdb.i().win:query_breakpoints()")

    def on_buf_leave(self):
        """Actions to execute when a buffer is left."""
        if self.vim.current.buffer.options['buftype'] == 'terminal':
            # Move the cursor to the end of the buffer
            self.vim.command("$")
            return
        if self.vim.exec_lua("return nvimgdb.i().win:is_jump_window_active()"):
            self.vim.exec_lua("nvimgdb.i().keymaps:dispatch_unset()")

    def lopen(self, kind, mods):
        """Load backtrace or breakpoints into the location list."""
        cmd = ''
        if kind == "backtrace":
            cmd = self.vim.exec_lua("return nvimgdb.i().backend:translate_command('bt')")
        elif kind == "breakpoints":
            cmd = self.vim.exec_lua("return nvimgdb.i().backend:translate_command('info breakpoints')")
        else:
            self.logger.warning("Unknown lopen kind %s", kind)
            return
        self.vim.exec_lua(f"nvimgdb.i().win:lopen('{cmd}', '{kind}', '{mods}')")

    def get_for_llist(self, kind, cmd):
        output = self.vim.exec_lua(f"return nvimgdb.i():custom_command('{cmd}')")
        lines = re.split(r'[\r\n]+', output)
        if kind == "backtrace":
            return lines
        elif kind == "breakpoints":
            return lines
        else:
            self.logger.warning("Unknown lopen kind %s", kind)
