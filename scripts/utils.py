"""Compatibility import for the shared DMCB utility module."""

import sys

from dmcb import utils

sys.modules[__name__] = utils
