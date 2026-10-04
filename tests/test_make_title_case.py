import os
import sys
import unittest

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.text_formatter import make_title_case


class TestPlayerKey(unittest.TestCase):
    def test_make_player_key(self):
        self.assertEqual(make_title_case("sign and trade deal"), "Sign-and-Trade Deal")
        self.assertEqual(make_title_case("non taxpayer bi annual mle"), "Non-Taxpayer Bi-Annual MLE")
        self.assertEqual(make_title_case("la-lakers"), "LA Lakers")
        self.assertEqual(make_title_case("philadelphia-76ers"), "Philadelphia 76ers")
        self.assertEqual(make_title_case("non-bird-rights"), "Non-Bird Rights")
        self.assertEqual(make_title_case("room-mid-level-exception"), "Room Mid-Level Exception")


if __name__ == "__main__":
    unittest.main()
