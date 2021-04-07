from __future__ import annotations

from collections import defaultdict
from collections.abc import MutableMapping
from typing import TypeVar

_K = TypeVar("_K")
_V = TypeVar("_V")


class _CaseInsensitiveDict(MutableMapping[_K, _V]):
    # Base on https://stackoverflow.com/a/32888599 but tweaked for python3
    @staticmethod
    def _k(key):
        return key.lower() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # type: ignore
        self._convert_keys()

    def __getitem__(self, key):
        return super().__getitem__(self._k(key))

    def __setitem__(self, key, value):
        super().__setitem__(self._k(key), value)

    def __delitem__(self, key):
        return super().__delitem__(self._k(key))

    def __contains__(self, key):
        return super().__contains__(self._k(key))

    def pop(self, key, *args, **kwargs):
        return super().pop(self._k(key), *args, **kwargs)

    def get(self, key, *args, **kwargs):
        return super().get(self._k(key), *args, **kwargs)

    def setdefault(self, key, *args, **kwargs):
        return super().setdefault(self._k(key), *args, **kwargs)

    def _convert_keys(self):
        for k in list(self.keys()):
            v = super().pop(k)
            self.__setitem__(k, v)


class CaseInsensitiveDict(_CaseInsensitiveDict[_K, _V], dict[_K, _V]):
    pass


class CaseInsensitiveDefaultDict(_CaseInsensitiveDict[_K, _V], defaultdict[_K, _V]):
    pass
