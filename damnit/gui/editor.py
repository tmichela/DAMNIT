import sys
from enum import Enum
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.Qsci import QsciScintilla, QsciLexerPython, QsciCommand

from pyflakes.reporter import Reporter
from pyflakes.api import check as pyflakes_check
from superqt.utils import thread_worker

from ..backend.extract_data import get_context_file


class ContextTestResult(Enum):
    OK = 0
    WARNING = 1
    ERROR = 2


@thread_worker
def check_context_file(code, db_dir, context_python):
    print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
    # Write the context to a temporary file to evaluate it from another
    # process.
    with NamedTemporaryFile(prefix=".tmp_ctx", dir=db_dir) as ctx_file:
        ctx_path = Path(ctx_file.name)
        ctx_path.write_text(code)

        context_python = sys.executable if context_python is None else context_python
        ctx, error_info = get_context_file(ctx_path, context_python)

    if error_info is not None:
        stacktrace, lineno, offset = error_info
        print('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<,')
        return ContextTestResult.ERROR, stacktrace, lineno, offset, code

    # If that worked, try pyflakes
    out_buffer = StringIO()
    reporter = Reporter(out_buffer, out_buffer)
    pyflakes_check(code, "<ctx>", reporter)
    # Disgusting hack to avoid getting warnings for "var#foo", "meta#foo",
    # and "mymdc#foo" type annotations. This needs some tweaking to avoid
    # missing real errors.
    pyflakes_output = "\n".join([line for line in out_buffer.getvalue().split("\n")
                                    if not line.endswith("undefined name 'var'") \
                                    and not line.endswith("undefined name 'meta'") \
                                    and not line.endswith("undefined name 'mymdc'")])

    if len(pyflakes_output) > 0:
        res, info = ContextTestResult.WARNING, pyflakes_output
    else:
        res, info = ContextTestResult.OK, None
    print('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<,')
    return res, info, -1, -1, code


class Editor(QsciScintilla):
    check_result = pyqtSignal(object, str, str)  # result, info, checked_code

    def __init__(self):
        super().__init__()

        font = QFont("Monospace", pointSize=12)
        self._lexer = QsciLexerPython()
        self._lexer.setDefaultFont(font)
        self._lexer.setFont(font, QsciLexerPython.Comment)
        self.setLexer(self._lexer)

        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionThreshold(3)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setAutoIndent(True)
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor('lightgray'))
        self.setMarginWidth(0, "0000")
        self.setMarginLineNumbers(0, True)

        # Set Ctrl + D to delete a line
        commands = self.standardCommands()
        ctrl_d = commands.boundTo(Qt.ControlModifier | Qt.Key_D)
        ctrl_d.setKey(0)

        line_del = commands.find(QsciCommand.LineDelete)
        line_del.setKey(Qt.ControlModifier | Qt.Key_D)

    def launch_test_context(self, db):
        context_python = db.metameta.get("context_python")
        thread = check_context_file(self.text(), db.path.parent, context_python)
        thread.returned.connect(self.on_test_result)
        thread.start()

    def on_test_result(self, res, info, lineno, offset, checked_code):
        if res is ContextTestResult.ERROR:
            if lineno != -1:
                # The line numbers reported by Python are 1-indexed so we
                # decrement before passing them to scintilla.
                lineno -= 1

                self.ensureLineVisible(lineno)

                # If we're already at the line, don't move the cursor unnecessarily
                if lineno != self.getCursorPosition()[0]:
                    self.setCursorPosition(lineno, offset)

        self.check_result.emit(res, info, checked_code)