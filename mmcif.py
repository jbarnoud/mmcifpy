"""
Read PDBx/MMCIF files
"""

import collections
import re
import warnings

SPLIT_RE = re.compile(r'''((?:[^\s"']|"[^"]*"|'[^']*')+)''')


class LineIterator(object):
    def __init__(self, lines):
        self._lines = lines
        self._backlog = collections.deque()

    def __next__(self):
        line = self.peek()
        if line is None:
            raise StopIteration
        return self._backlog.popleft()

    def __iter__(self):
        return self

    def _next_or_none(self, iterator):
        try:
            line = next(iterator)
        except StopIteration:
            line = None
        return line

    def _pop_or_next(self):
        if len(self._backlog) > 0:
            line = self._backlog.popleft()
        else:
            line = self._next_or_none(self._lines)
        return line


    def peek(self):
        line = self._pop_or_next()
        if line is not None and line[0] == ';':
            while True:
                next_line = self._pop_or_next()
                if next_line is None or next_line.startswith(';'):
                    break
                else:
                    line = line[:-1] + next_line

        self._backlog.append(line)

        return line


class Reader(object):
    def __init__(self):
        self.record_starts = {'_': self._parse_entry,
                              'loop_': self._parse_loop,
                              '#': self._parse_comment,}
        self._records = collections.OrderedDict()

    def parse(self, lines):
        lines_iter = LineIterator(lines)
        for line in lines_iter:
            for start, method in self.record_starts.items():
                if line.startswith(start):
                    method(line, lines_iter)
                    break
            else:
                warnings.warn('Unexpected line "{}".'.format(line))

    def _parse_entry(self, line, lines_iter):
        tokens = self._get_tokens(line)
        if len(tokens) < 2:
            tokens += self._get_tokens(next(lines_iter))
        root, entry = tokens[0][1:].split('.')
        self._records[root] = self._records.get(root, collections.OrderedDict())
        self._records[root][entry] = ' '.join(tokens[1:])

    def _parse_comment(self, line, lines_iter):
        pass

    def _parse_loop(self, line, lines_iter):
        keys = []
        entries = []
        while lines_iter.peek().startswith('_'):
            line = next(lines_iter)
            try:
                root, key = line[1:].strip().split('.')
            except ValueError as e:
                print(line)
                raise e
            keys.append(key)
        while not self._is_record(lines_iter.peek()):
            line = next(lines_iter)
            tokens = self._get_tokens(line)
            while len(tokens) < len(keys):
                tokens += self._get_tokens(next(lines_iter))
            entry = collections.OrderedDict(list(zip(keys, tokens)))
            entries.append(entry)
        self._records[root] = entries

    def _is_record(self, line):
        if line is None:
            return False
        for start in self.record_starts.keys():
            if line.startswith(start):
                return True
        return False

    def _get_tokens(self, line):
        tokens = SPLIT_RE.split(line)[1::2]
        tokens = [token[1:-1] if token[0] == token[-1] and token[0] in '\'"'
                  else token for token in tokens]
        totens = [token.strip() for token in tokens]
        return tokens
