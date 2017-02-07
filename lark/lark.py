from __future__ import absolute_import

import os

from .utils import STRING_TYPE, inline_args
from .load_grammar import load_grammar
from .tree import Tree, Transformer

from .lexer import Lexer
from .parse_tree_builder import ParseTreeBuilder
from .parser_frontends import ENGINE_DICT

class LarkOptions(object):
    """Specifies the options for Lark

    """
    OPTIONS_DOC = """
        parser - Which parser engine to use ("earley" or "lalr". Default: "earley")
                 Note: Both will use Lark's lexer.
        transformer - Applies the transformer to every parse tree
        debug - Affects verbosity (default: False)
        only_lex - Don't build a parser. Useful for debugging (default: False)
        keep_all_tokens - Don't automagically remove "punctuation" tokens (default: True)
        cache_grammar - Cache the Lark grammar (Default: False)
        postlex - Lexer post-processing (Default: None)
        start - The start symbol (Default: start)
    """
    __doc__ += OPTIONS_DOC
    def __init__(self, options_dict):
        o = dict(options_dict)

        self.debug = bool(o.pop('debug', False))
        self.only_lex = bool(o.pop('only_lex', False))
        self.keep_all_tokens = bool(o.pop('keep_all_tokens', False))
        self.tree_class = o.pop('tree_class', Tree)
        self.cache_grammar = o.pop('cache_grammar', False)
        self.postlex = o.pop('postlex', None)
        self.parser = o.pop('parser', 'earley')
        self.transformer = o.pop('transformer', None)
        self.start = o.pop('start', 'start')

        assert self.parser in ENGINE_DICT
        if self.parser == 'earley' and self.transformer:
            raise ValueError('Cannot specify an auto-transformer when using the Earley algorithm. Please use your transformer on the resulting parse tree, or use a different algorithm (i.e. lalr)')
        if self.keep_all_tokens:
            raise NotImplementedError("Not implemented yet!")

        if o:
            raise ValueError("Unknown options: %s" % o.keys())




class Lark:
    def __init__(self, grammar, **options):
        """
            grammar : a string or file-object containing the grammar spec (using Lark's ebnf syntax)
            options : a dictionary controlling various aspects of Lark.
        """
        self.options = LarkOptions(options)

        # Some, but not all file-like objects have a 'name' attribute
        try:
            source = grammar.name
        except AttributeError:
            source = '<string>'
            cache_file = "larkcache_%s" % str(hash(grammar)%(2**32))
        else:
            cache_file = "larkcache_%s" % os.path.basename(source)

        # Drain file-like objects to get their contents
        try:
            read = grammar.read
        except AttributeError:
            pass
        else:
            grammar = read()

        assert isinstance(grammar, STRING_TYPE)

        if self.options.cache_grammar:
            raise NotImplementedError("Not available yet")

        self.tokens, self.rules = load_grammar(grammar)

        self.lexer = self._build_lexer()
        if not self.options.only_lex:
            self.parser_engine = ENGINE_DICT[self.options.parser]()
            self.parse_tree_builder = ParseTreeBuilder(self.options.tree_class)
            self.parser = self._build_parser()

    def _build_lexer(self):
        ignore_tokens = []
        tokens = []
        for name, value, flags in self.tokens:
            if 'ignore' in flags:
                ignore_tokens.append(name)
            tokens.append((name, value))
        return Lexer(tokens, {}, ignore=ignore_tokens)


    def _build_parser(self):
        rules, callback = self.parse_tree_builder.create_tree_builder(self.rules, self.options.transformer)
        return self.parser_engine.build_parser(rules, callback, self.options.start)


    __init__.__doc__ += "\nOPTIONS:" + LarkOptions.OPTIONS_DOC

    def lex(self, text):
        stream = self.lexer.lex(text)
        if self.options.postlex:
            return self.options.postlex.process(stream)
        else:
            return stream

    def parse(self, text):
        assert not self.options.only_lex
        l = list(self.lex(text))
        return self.parser.parse(l)

