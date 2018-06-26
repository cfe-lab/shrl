import unittest

import shrl.io


class TestDowncaseHeaders(unittest.TestCase):
    def test_downcase_first_line(self):
        source = iter([
            "A,B,C",
            "X,Y,Z",
        ])
        expecteds = iter([
            "a,b,c",
            "X,Y,Z",
        ])
        pairs = zip(shrl.io._downcase_csv_headers(source), expecteds)
        for calculated, expected in pairs:
            self.assertEqual(calculated, expected)
