import ast
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class FunctionDefinition:
    name: str
    file_path: str
    start_line: int
    end_line: int
    code_snippet: str
    docstring: Optional[str] = None


@dataclass
class SemanticCodeContext:
    failing_file: str
    failing_line: int
    enclosing_function: Optional[str]
    enclosing_class: Optional[str]
    called_functions: List[str]
    resolved_cross_file_definitions: List[FunctionDefinition]
    formatted_context_block: str


class ASTNavigator:
    """AST-based Semantic Code Navigator for extracting call graphs and cross-file definitions."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = os.path.abspath(workspace_root)
        self._file_ast_cache: Dict[str, Tuple[ast.AST, List[str]]] = {}

    def _get_ast(self, file_path: str) -> Optional[Tuple[ast.AST, List[str]]]:
        """Parse source file into AST, caching results."""
        abs_path = os.path.abspath(file_path)
        if abs_path in self._file_ast_cache:
            return self._file_ast_cache[abs_path]

        if not os.path.exists(abs_path):
            return None

        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
                lines = code.splitlines()
                tree = ast.parse(code, filename=abs_path)
                self._file_ast_cache[abs_path] = (tree, lines)
                return tree, lines
        except Exception:
            return None

    def find_enclosing_scope(self, file_path: str, line_number: int) -> Tuple[Optional[str], Optional[str]]:
        """Find the enclosing function name and class name for a specific line number."""
        parsed = self._get_ast(file_path)
        if not parsed:
            return None, None

        tree, _ = parsed
        enclosing_func = None
        enclosing_class = None

        class Visitor(ast.NodeVisitor):
            def __init__(self):
                self.curr_class = None

            def visit_ClassDef(self, node: ast.ClassDef):
                old_class = self.curr_class
                self.curr_class = node.name
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    if node.lineno <= line_number <= node.end_lineno:
                        nonlocal enclosing_class
                        enclosing_class = node.name
                self.generic_visit(node)
                self.curr_class = old_class

            def visit_FunctionDef(self, node: ast.FunctionDef):
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    if node.lineno <= line_number <= node.end_lineno:
                        nonlocal enclosing_func
                        enclosing_func = node.name
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    if node.lineno <= line_number <= node.end_lineno:
                        nonlocal enclosing_func
                        enclosing_func = node.name
                self.generic_visit(node)

        Visitor().visit(tree)
        return enclosing_func, enclosing_class

    def extract_called_functions(self, file_path: str, start_line: int, end_line: int) -> List[str]:
        """Extract all function call names within a line range."""
        parsed = self._get_ast(file_path)
        if not parsed:
            return []

        tree, _ = parsed
        called: List[str] = []

        class CallVisitor(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call):
                if hasattr(node, "lineno") and start_line <= node.lineno <= end_line:
                    if isinstance(node.func, ast.Name):
                        called.append(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        called.append(node.func.attr)
                self.generic_visit(node)

        CallVisitor().visit(tree)
        return list(set(called))

    def resolve_import_sources(self, file_path: str) -> Dict[str, str]:
        """Map imported symbols to their workspace file paths."""
        parsed = self._get_ast(file_path)
        if not parsed:
            return {}

        tree, _ = parsed
        symbol_to_file: Dict[str, str] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                module_parts = node.module.split(".")
                potential_file = os.path.join(self.workspace_root, *module_parts) + ".py"
                if not os.path.exists(potential_file):
                    potential_file = os.path.join(self.workspace_root, *module_parts, "__init__.py")

                if os.path.exists(potential_file):
                    for alias in node.names:
                        symbol_to_file[alias.asname or alias.name] = potential_file

        return symbol_to_file

    def get_function_definition(self, file_path: str, target_func_name: str) -> Optional[FunctionDefinition]:
        """Find the AST definition of a target function in a given file."""
        parsed = self._get_ast(file_path)
        if not parsed:
            return None

        tree, lines = parsed
        res = None

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target_func_name:
                start = node.lineno
                end = getattr(node, "end_lineno", start + 20)
                snippet = "\n".join(lines[start - 1:end])
                doc = ast.get_docstring(node)
                res = FunctionDefinition(
                    name=target_func_name,
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    code_snippet=snippet,
                    docstring=doc,
                )
                break

        return res

    def get_semantic_context(self, file_path: str, line_number: int, context_range: int = 5) -> SemanticCodeContext:
        """Perform semantic navigation across the call graph and return formatted context."""
        abs_path = os.path.abspath(file_path)
        enc_func, enc_class = self.find_enclosing_scope(abs_path, line_number)
        called_funcs = self.extract_called_functions(abs_path, max(1, line_number - context_range), line_number + context_range)

        import_map = self.resolve_import_sources(abs_path)
        cross_file_defs: List[FunctionDefinition] = []

        for func_name in called_funcs:
            if func_name in import_map:
                target_file = import_map[func_name]
                func_def = self.get_function_definition(target_file, func_name)
                if func_def:
                    cross_file_defs.append(func_def)

        # Build formatted context block
        block_lines = [
            f"=== SEMANTIC CODE NAVIGATION CONTEXT ===",
            f"Failing File: {os.path.basename(file_path)} (Line {line_number})",
            f"Enclosing Scope: {f'{enc_class}.{enc_func}' if enc_class and enc_func else enc_func or enc_class or '<global module>'}",
        ]

        if called_funcs:
            block_lines.append(f"Detected Function Calls: {', '.join(called_funcs)}")

        if cross_file_defs:
            block_lines.append("\n--- AST Resolved Cross-File Definitions ---")
            for cfd in cross_file_defs:
                block_lines.append(f"\n[Imported Function: {cfd.name} from {os.path.basename(cfd.file_path)} (Lines {cfd.start_line}-{cfd.end_line})]")
                block_lines.append(cfd.code_snippet)

        formatted_block = "\n".join(block_lines)

        return SemanticCodeContext(
            failing_file=file_path,
            failing_line=line_number,
            enclosing_function=enc_func,
            enclosing_class=enc_class,
            called_functions=called_funcs,
            resolved_cross_file_definitions=cross_file_defs,
            formatted_context_block=formatted_block,
        )
