import os
import sys
import unittest

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.text_formatter import make_player_key


class TestPlayerKey(unittest.TestCase):
    def test_make_player_key(self):
        self.assertEqual(make_player_key("A.J. Green"), "aj-green")
        self.assertEqual(make_player_key("Alperen Şengün"), "alperen-sengun")
        self.assertEqual(make_player_key("Cam Thomas"), "cameron-thomas")
        self.assertEqual(make_player_key("Collin Murray-Boyles"), "collin-murray-boyles")
        self.assertEqual(make_player_key("Darius Brown II"), "darius-brown")
        self.assertEqual(make_player_key("De'Aaron Fox"), "deaaron-fox")
        self.assertEqual(make_player_key("Jabari Smith Jr."), "jabari-smith")
        self.assertEqual(make_player_key("Olivier-Maxence Prosper"), "olivier-maxence-prosper")
        self.assertEqual(make_player_key("Trey Murphy III"), "trey-murphy")
        self.assertEqual(make_player_key("Xavier Tillman Sr."), "xavier-tillman")
        self.assertEqual(make_player_key("Yang Hansen"), "yang-hansen")


if __name__ == "__main__":
    unittest.main()
