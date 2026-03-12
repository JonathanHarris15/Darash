import pytest
from src.core.search_engine import SearchEngine, tokenize, Parser, TokenType

# Mock verse data for testing
mock_verses = [
    {'book': 'Genesis', 'chapter': '1', 'verse_num': '1', 'text': 'In the beginning God created the heavens and the earth.'},
    {'book': 'Genesis', 'chapter': '1', 'verse_num': '2', 'text': 'The earth was without form, and void; and darkness was on the face of the deep.'},
    {'book': 'Genesis', 'chapter': '2', 'verse_num': '1', 'text': 'Thus the heavens and the earth were finished.'},
    {'book': 'Exodus', 'chapter': '20', 'verse_num': '1', 'text': 'And God spoke all these words, saying,'},
    {'book': 'Exodus', 'chapter': '20', 'verse_num': '2', 'text': 'I am the LORD your God, who brought you out of the land of Egypt.'},
    {'book': 'Romans', 'chapter': '5', 'verse_num': '1', 'text': 'Therefore, since we have been justified by faith, we have peace with God.'},
    {'book': 'Romans', 'chapter': '5', 'verse_num': '21', 'text': 'so that, as sin reigned in death, grace also might reign through righteousness leading to eternal life.'},
    {'book': 'Galatians', 'chapter': '3', 'verse_num': '11', 'text': 'Now it is evident that no one is justified before God by the law, for "The righteous shall live by faith."'},
    {'book': 'Galatians', 'chapter': '3', 'verse_num': '12', 'text': 'But the law is not of faith, rather "The one who does them shall live by them."'}
]

def test_tokenizer():
    tokens = tokenize('verse: law AND faith OR (righteousness XOR grace) NOT deep')
    types = [t[0] for t in tokens]
    expected = [
        TokenType.SCOPE, TokenType.WORD, TokenType.AND, TokenType.WORD, TokenType.OR,
        TokenType.LPAREN, TokenType.WORD, TokenType.XOR, TokenType.WORD, TokenType.RPAREN,
        TokenType.NOT, TokenType.WORD, TokenType.EOF
    ]
    assert types == expected

def test_tokenizer_phrases():
    tokens = tokenize('"living God" AND faith')
    assert tokens[0] == (TokenType.WORD, 'living God')
    assert tokens[1] == (TokenType.AND, 'AND')

def test_parser_basic_and():
    tokens = tokenize('law AND faith')
    ast = Parser(tokens).parse()
    assert ast.__class__.__name__ == 'AndNode'
    assert ast.left.word == 'law'
    assert ast.right.word == 'faith'

def test_parser_implicit_and():
    tokens = tokenize('law faith')
    ast = Parser(tokens).parse()
    assert ast.__class__.__name__ == 'AndNode'

def test_parser_not():
    tokens = tokenize('NOT law')
    ast = Parser(tokens).parse()
    assert ast.__class__.__name__ == 'NotNode'

def test_parser_parens_precedence():
    tokens = tokenize('law AND (faith OR grace)')
    ast = Parser(tokens).parse()
    assert ast.__class__.__name__ == 'AndNode'
    assert ast.right.__class__.__name__ == 'OrNode'

def test_parser_top_level_scope():
    tokens = tokenize('chapter: law AND faith')
    ast = Parser(tokens).parse()
    assert ast.__class__.__name__ == 'ScopeNode'
    assert ast.scope_type == 'chapter'
    assert ast.child.__class__.__name__ == 'AndNode'

def test_parser_nested_scope():
    tokens = tokenize('law AND chapter: faith')
    ast = Parser(tokens).parse()
    assert ast.__class__.__name__ == 'AndNode'
    assert ast.right.__class__.__name__ == 'ScopeNode'

def test_search_engine_verse_scope_basic():
    engine = SearchEngine(mock_verses)
    results = engine.search('earth')
    assert len(results) == 3
    assert results[0].display_ref == 'Genesis 1:1'
    assert results[1].display_ref == 'Genesis 1:2'
    assert results[2].display_ref == 'Genesis 2:1'

def test_search_engine_and():
    engine = SearchEngine(mock_verses)
    results = engine.search('heavens AND earth')
    # Gen 1:1 and Gen 2:1 have both
    assert len(results) == 2

def test_search_engine_or():
    engine = SearchEngine(mock_verses)
    results = engine.search('justified OR darkness')
    assert len(results) == 3 # Rom 5:1, Gal 3:11, Gen 1:2

def test_search_engine_not():
    engine = SearchEngine(mock_verses)
    results = engine.search('God AND NOT earth')
    assert len(results) == 4 # Ex 20:1, Ex 20:2, Rom 5:1, Gal 3:11

def test_search_engine_xor():
    engine = SearchEngine(mock_verses)
    results = engine.search('justified XOR faith')
    # Rom 5:1 has both ('justified by faith') -> False
    # Gal 3:11 has both ('justified... faith.') -> False
    # Wait, Gal 3:12 has 'faith' but no 'justified'
    assert len(results) == 1
    assert results[0].display_ref == 'Galatians 3:12'

def test_search_engine_top_level_chapter():
    engine = SearchEngine(mock_verses)
    results = engine.search('chapter: heavens')
    assert len(results) == 2
    assert results[0].display_ref == 'Genesis 1'
    assert results[1].display_ref == 'Genesis 2'

def test_search_engine_chapter_cross_verse_and():
    engine = SearchEngine(mock_verses)
    # the chapter Gen 1 has 'beginning' in v1 and 'darkness' in v2
    # So if we search chapter scope, it should match Gen 1
    results = engine.search('chapter: beginning AND darkness')
    assert len(results) == 1
    assert results[0].display_ref == 'Genesis 1'
    
    # but verse scope shouldn't match
    results_v = engine.search('verse: beginning AND darkness')
    assert len(results_v) == 0

def test_search_engine_nested_scope():
    engine = SearchEngine(mock_verses)
    # Find verses having "faith" where the enclosing chapter also has "death"
    # Romans 5:1 has "faith", Romans 5:21 has "death", so Romans 5 has "death"
    results = engine.search('faith AND chapter: death')
    assert len(results) == 1
    assert results[0].display_ref == 'Romans 5:1'
    
    # Galatians 3 has "faith", but no "death"
    # so it shouldn't match.

def test_search_engine_nested_scope_widening():
    engine = SearchEngine(mock_verses)
    # Find books having both 'beginning' and 'egypt'
    # Genesis has beginning, no egypt.
    # Exodus has egypt, no beginning.
    # No book should match
    results = engine.search('book: beginning AND egypt')
    assert len(results) == 0

    # Test top-level chapter checking for verses
    # Chapter: find chapters that have a verse with 'faith' AND a verse with 'death'
    # (implicitly chapter evaluates the components on its own text)
    results = engine.search('chapter: (verse: faith) AND (verse: death)')
    assert len(results) == 1
    assert results[0].display_ref == 'Romans 5'
