from docutils.core import publish_doctree
from docutils import nodes


class PythonCodeBlockExtractor(nodes.NodeVisitor):
    """
    A custom NodeVisitor that extracts Python code blocks from a
    docutils document tree.
    """
    def __init__(self, document):
        super().__init__(document)
        self.code_blocks = []

    def visit_literal_block(self, node):
        # Check if the block has 'python' specified in its classes
        if 'python' in node.get('classes', []):
            # Extract the raw code text inside the block
            self.code_blocks.append(node.astext())

    def unknown_visit(self, node):
        pass  # Ignore other node types


def extract_python_code(rst_text):
    # Parse the RST text into an internal document tree
    doctree = publish_doctree(rst_text)

    # Initialize the visitor and walk the tree
    extractor = PythonCodeBlockExtractor(doctree)
    doctree.walk(extractor)

    return extractor.code_blocks

