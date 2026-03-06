import re

class TokenType:
    SCOPE = 'SCOPE'
    AND = 'AND'
    OR = 'OR'
    XOR = 'XOR'
    NOT = 'NOT'
    LPAREN = 'LPAREN'
    RPAREN = 'RPAREN'
    WORD = 'WORD'
    EOF = 'EOF'

def tokenize(text):
    tokens = []
    text = text.replace('(', ' ( ').replace(')', ' ) ')
    
    # Use global case-insensitive flag at the start
    pattern = r'(?i)"[^"]*"|(?:verse|chapter|book)\s*:|\(|\)|\band\b|\bor\b|\bxor\b|\bnot\b|[^\s\(\)]+'
    
    matches = re.finditer(pattern, text)
    for m in matches:
        val = m.group(0).strip()
        lval = val.lower()
        if lval in ['verse:', 'chapter:', 'book:']:
            tokens.append((TokenType.SCOPE, lval[:-1].strip()))
        elif lval == 'and':
            tokens.append((TokenType.AND, val))
        elif lval == 'or':
            tokens.append((TokenType.OR, val))
        elif lval == 'xor':
            tokens.append((TokenType.XOR, val))
        elif lval == 'not':
            tokens.append((TokenType.NOT, val))
        elif val == '(':
            tokens.append((TokenType.LPAREN, val))
        elif val == ')':
            tokens.append((TokenType.RPAREN, val))
        elif val.startswith('"') and val.endswith('"'):
            tokens.append((TokenType.WORD, val[1:-1]))
        else:
            tokens.append((TokenType.WORD, lval)) # store lowercase for matching
            
    tokens.append((TokenType.EOF, ''))
    return tokens


class Node: pass

class WordNode(Node):
    def __init__(self, word): self.word = word
    def __repr__(self): return f"Word({self.word})"
    
class AndNode(Node):
    def __init__(self, left, right): self.left = left; self.right = right
    def __repr__(self): return f"And({self.left}, {self.right})"
    
class OrNode(Node):
    def __init__(self, left, right): self.left = left; self.right = right
    def __repr__(self): return f"Or({self.left}, {self.right})"
    
class XorNode(Node):
    def __init__(self, left, right): self.left = left; self.right = right
    def __repr__(self): return f"Xor({self.left}, {self.right})"
    
class NotNode(Node):
    def __init__(self, child): self.child = child
    def __repr__(self): return f"Not({self.child})"
    
class ScopeNode(Node):
    def __init__(self, scope_type, child): self.scope_type = scope_type; self.child = child
    def __repr__(self): return f"Scope({self.scope_type}, {self.child})"

class ParseError(Exception): pass

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        
    def current(self):
        return self.tokens[self.pos]
        
    def consume(self, expected_type=None):
        tok = self.current()
        if expected_type and tok[0] != expected_type:
            raise ParseError(f"Expected {expected_type}, got {tok[0]}")
        self.pos += 1
        return tok
        
    def parse(self):
        if self.current()[0] == TokenType.EOF:
            return None
        ast = self.parse_expr()
        if self.current()[0] != TokenType.EOF:
            raise ParseError(f"Unexpected token {self.current()} at end of parsing")
        return ast
        
    def parse_expr(self):
        tok = self.current()
        if tok[0] == TokenType.SCOPE:
            self.consume(TokenType.SCOPE)
            child = self.parse_subexpr()
            return ScopeNode(tok[1], child)
        else:
            return self.parse_subexpr()
            
    def parse_subexpr(self):
        node = self.parse_term()
        while self.current()[0] in (TokenType.OR, TokenType.XOR):
            op = self.consume()[0]
            right = self.parse_term()
            if op == TokenType.OR:
                node = OrNode(node, right)
            else:
                node = XorNode(node, right)
        return node
        
    def parse_term(self):
        node = self.parse_factor()
        while self.current()[0] == TokenType.AND:
            self.consume(TokenType.AND)
            right = self.parse_factor()
            node = AndNode(node, right)
        # Implicit AND
        while self.current()[0] in (TokenType.NOT, TokenType.LPAREN, TokenType.WORD, TokenType.SCOPE):
            right = self.parse_factor()
            node = AndNode(node, right)
        return node
        
    def parse_factor(self):
        if self.current()[0] == TokenType.NOT:
            self.consume(TokenType.NOT)
            return NotNode(self.parse_atom())
        return self.parse_atom()
        
    def parse_atom(self):
        tok = self.current()
        if tok[0] == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            node = self.parse_expr()
            self.consume(TokenType.RPAREN)
            return node
        elif tok[0] == TokenType.WORD:
            return WordNode(self.consume(TokenType.WORD)[1])
        elif tok[0] == TokenType.SCOPE:
            return self.parse_expr()
        else:
            raise ParseError(f"Unexpected token {tok} in parse_atom")


class SearchContext:
    def __init__(self, type, verses, book=None, chapter=None, verse_num=None):
        self.type = type
        self.verses = verses
        self.book = book
        self.chapter = chapter
        self.verse_num = verse_num
        self.text = " ".join(v['text'] for v in verses).lower()

class SearchResult:
    def __init__(self, scope, display_ref, scroll_ref):
        self.scope = scope
        self.display_ref = display_ref
        self.scroll_ref = scroll_ref
        
    def __repr__(self):
        return f"SearchResult({self.scope}, '{self.display_ref}')"


class SearchEngine:
    def __init__(self, flat_verses):
        self.flat_verses = flat_verses
        self.books = {}
        self.chapters = {}
        for v in flat_verses:
            self.books.setdefault(v['book'], []).append(v)
            chap_id = f"{v['book']} {v['chapter']}"
            self.chapters.setdefault(chap_id, []).append(v)

    def search(self, query_str):
        if not query_str.strip():
            return []
            
        try:
            tokens = tokenize(query_str)
            ast = Parser(tokens).parse()
            if not ast: return []
        except ParseError as e:
            print(f"Search Parse Error: {e}")
            return []

        top_scope = 'verse'
        if isinstance(ast, ScopeNode):
            top_scope = ast.scope_type
            
        contexts = self.get_all_contexts(top_scope)
        results = []
        for ctx in contexts:
            if self.evaluate_node(ast, ctx):
                if top_scope == 'verse':
                    ref = f"{ctx.book} {ctx.chapter}:{ctx.verse_num}"
                    results.append(SearchResult('verse', ref, ref))
                elif top_scope == 'chapter':
                    ref = f"{ctx.book} {ctx.chapter}"
                    results.append(SearchResult('chapter', ref, f"{ref}:1"))
                elif top_scope == 'book':
                    results.append(SearchResult('book', ctx.book, f"{ctx.book} 1:1"))
        return results

    def get_all_contexts(self, scope_type):
        contexts = []
        if scope_type == 'verse':
            for v in self.flat_verses:
                contexts.append(SearchContext('verse', [v], v['book'], v['chapter'], v['verse_num']))
        elif scope_type == 'chapter':
            for chap_id, verses in self.chapters.items():
                contexts.append(SearchContext('chapter', verses, verses[0]['book'], verses[0]['chapter']))
        elif scope_type == 'book':
            for book, verses in self.books.items():
                contexts.append(SearchContext('book', verses, book))
        return contexts

    def evaluate_node(self, node, ctx):
        if isinstance(node, WordNode):
            return node.word in ctx.text
        elif isinstance(node, AndNode):
            return self.evaluate_node(node.left, ctx) and self.evaluate_node(node.right, ctx)
        elif isinstance(node, OrNode):
            return self.evaluate_node(node.left, ctx) or self.evaluate_node(node.right, ctx)
        elif isinstance(node, XorNode):
            l = self.evaluate_node(node.left, ctx)
            r = self.evaluate_node(node.right, ctx)
            return (l and not r) or (not l and r)
        elif isinstance(node, NotNode):
            return not self.evaluate_node(node.child, ctx)
        elif isinstance(node, ScopeNode):
            return self.evaluate_scope(node.scope_type, node.child, ctx)
        raise ValueError(f"Unknown node type: {type(node)}")
        
    def evaluate_scope(self, target_scope_type, child_node, current_ctx):
        if target_scope_type == current_ctx.type:
            return self.evaluate_node(child_node, current_ctx)
            
        hier = {'verse': 0, 'chapter': 1, 'book': 2, 'bible': 3}
        curr_lvl = hier[current_ctx.type]
        tgt_lvl = hier[target_scope_type]
        
        if tgt_lvl < curr_lvl: # Narrowing (e.g. chapter -> verse)
            if target_scope_type == 'verse':
                sub_ctxs = [SearchContext('verse', [v], v['book'], v['chapter'], v['verse_num']) for v in current_ctx.verses]
            elif target_scope_type == 'chapter':
                c_groups = {}
                for v in current_ctx.verses:
                    chap_id = f"{v['book']} {v['chapter']}"
                    c_groups.setdefault(chap_id, []).append(v)
                sub_ctxs = [SearchContext('chapter', vs, vs[0]['book'], vs[0]['chapter']) for vs in c_groups.values()]
            else: # book
                b_groups = {}
                for v in current_ctx.verses:
                    b_groups.setdefault(v['book'], []).append(v)
                sub_ctxs = [SearchContext('book', vs, vs[0]['book']) for vs in b_groups.values()]
                
            return any(self.evaluate_node(child_node, c) for c in sub_ctxs)
            
        else: # Widening (e.g. verse -> chapter)
            if target_scope_type == 'chapter':
                chap_id = f"{current_ctx.book} {current_ctx.chapter}"
                vs = self.chapters[chap_id]
                new_ctx = SearchContext('chapter', vs, current_ctx.book, current_ctx.chapter)
            elif target_scope_type == 'book':
                vs = self.books[current_ctx.book]
                new_ctx = SearchContext('book', vs, current_ctx.book)
            else: # bible
                # though bible scope wasn't requested, we could handle it here if it exists
                new_ctx = SearchContext('bible', self.flat_verses)
                
            return self.evaluate_node(child_node, new_ctx)
