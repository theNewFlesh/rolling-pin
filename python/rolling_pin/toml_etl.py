from typing import Any, Union

from copy import deepcopy
from pathlib import Path
import os

import toml

from rolling_pin.blob_etl import BlobETL
# ------------------------------------------------------------------------------


class TomlEtlEncoder(toml.TomlArraySeparatorEncoder):
    def __init__(self, _dict=dict, preserve=False, separator=','):
        # type: (dict, bool, str) -> None
        super().__init__(_dict, preserve, ',\n   ')

    def dump_list(self, v):
        # type: (list) -> str
        if len(v) == 0:
            return '[]'
        if len(v) == 1:
            return '["' + v[0] + '"]'
        output = super().dump_list(v)[1:-1].rstrip('    \n')
        return '[\n   ' + output + '\n]'


class TomlEtl:
    @classmethod
    def from_string(cls, text):
        # type: (TomlEtl, str) -> TomlEtl
        return cls(toml.loads(text))

    @classmethod
    def from_file(cls, filepath):
        # type: (TomlEtl, Union[str, Path]) -> TomlEtl
        return cls(toml.load(filepath))

    def to_dict(self):
        # type: () -> dict
        return deepcopy(self._data)

    def to_string(self):
        # type: () -> str
        return toml.dumps(self._data, encoder=TomlEtlEncoder())

    def to_file(self, filepath):
        # type: (Union[str, Path]) -> None
        filepath = Path(filepath)
        os.makedirs(filepath.parent, exist_ok=True)
        with open(filepath, 'w') as f:
            toml.dump(self._data, f, encoder=TomlEtlEncoder())

    def __init__(self, data):
        # type: (dict[str, Any]) -> None
        self._data = data

    def edit(self, key, value):
        # type: (str, str) -> TomlEtl
        data = BlobETL(self._data, separator='.').to_flat_dict()
        if value == ':DELETE:':
            del data[key]
        else:
            data[key] = value
        data = BlobETL(data, separator='.').to_dict()
        return TomlEtl(data)
