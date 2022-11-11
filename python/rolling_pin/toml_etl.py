from typing import Any, Dict, Type, TypeVar, Union

from copy import deepcopy
from pathlib import Path
import os

import toml

from rolling_pin.blob_etl import BlobETL

T = TypeVar('T', bound='TomlETL')
# ------------------------------------------------------------------------------


class TomlEtlEncoder(toml.TomlArraySeparatorEncoder):
    def __init__(self, _dict=dict, preserve=False, separator=','):
        # type: (Type[Dict[Any, Any]], bool, str) -> None
        super().__init__(_dict, preserve, ',\n   ')

    def dump_list(self, v):
        # type: (Any) -> str
        if len(v) == 0:
            return '[]'
        if len(v) == 1:
            return '["' + v[0] + '"]'
        output = super().dump_list(v)[1:-1].rstrip('    \n')
        return '[\n   ' + output + '\n]'


class TomlETL:
    @classmethod
    def from_string(cls, text):
        # type: (Type[T], str) -> T
        return cls(toml.loads(text))

    @classmethod
    def from_file(cls, filepath):
        # type: (Type[T], Union[str, Path]) -> T
        return cls(toml.load(filepath))

    def __init__(self, data):
        # type: (dict[str, Any]) -> None
        self._data = data

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

    def edit(self, patch):
        # type: (str) -> TomlETL
        key, val = patch.split('=', maxsplit=1)
        val = toml.loads(f'x={val}')['x']
        data = BlobETL(self._data, separator='.').to_flat_dict()
        if val == ':DELETE:':
            del data[key]
        else:
            data[key] = val
        data = BlobETL(data, separator='.').to_dict()
        return TomlETL(data)
