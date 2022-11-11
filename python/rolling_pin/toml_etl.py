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
        '''
        Creates a TomlEtlEncoder instance.

        Args:
            _dict (type, optional): Object type. Default: dict.
            preserve (bool, optional): Preserve inline tables. Default: False.
            separator (str, optional): List item separator. Default: ','.
        '''
        super().__init__(_dict, preserve, ',\n   ')

    def dump_list(self, v):
        # type: (Any) -> str
        '''
        Converts list of items to TOML formatted string.

        Args:
            v (list): List to be converted.

        Returns:
            str: TOML formatted list.
        '''
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
        '''
        Creates a TomlETL instance from a given TOML string.

        Args:
            text (str): TOML string.

        Returns:
            TomlETL: TomlETL instance.
        '''
        return cls(toml.loads(text))

    @classmethod
    def from_toml(cls, filepath):
        # type: (Type[T], Union[str, Path]) -> T
        '''
        Creates a TomlETL instance from a given TOML file.

        Args:
            filepath (str or Path): TOML file.

        Returns:
            TomlETL: TomlETL instance.
        '''
        return cls(toml.load(filepath))

    def __init__(self, data):
        # type: (dict[str, Any]) -> None
        '''
        Creates a TomlETL instance from a given dictionary.

        Args:
            data (dict): Dictionary.
        '''
        self._data = data

    def to_dict(self):
        # type: () -> dict
        '''
        Converts instance to dictionary copy.

        Returns:
            dict: Dictionary copy of instance.
        '''
        return deepcopy(self._data)

    def to_string(self):
        # type: () -> str
        '''
        Converts instance to a TOML formatted string.

        Returns:
            str: TOML string.
        '''
        return toml.dumps(self._data, encoder=TomlEtlEncoder())

    def to_file(self, filepath):
        # type: (Union[str, Path]) -> None
        '''
        Writes instance to given TOML file.

        Args:
            filepath (str or Path): Target filepath.
        '''
        filepath = Path(filepath)
        os.makedirs(filepath.parent, exist_ok=True)
        with open(filepath, 'w') as f:
            toml.dump(self._data, f, encoder=TomlEtlEncoder())

    def edit(self, patch):
        # type: (str) -> TomlETL
        '''
        Apply edit to internal data given TOML patch.
        Patch is always of the form '[key]=[value]' and in TOML format.
        If value is "<DELETE>" the given key will be deleted, otherwise it will
        be replaced with the given value.

        Args:
            patch (str): TOML patch to be applied.

        Raises:
            TomlDecoderError: If patch cannot be decoded.
            AssertionError: If '=' not found in patch.

        Returns:
            TomlETL: New TomlETL instance with edits.
        '''
        toml.loads(patch)
        assert '=' in patch
        # ----------------------------------------------------------------------

        key, val = patch.split('=', maxsplit=1)
        val = toml.loads(f'x={val}')['x']
        data = BlobETL(self._data, separator='.').to_flat_dict()
        if val == '<DELETE>':
            del data[key]
        else:
            data[key] = val
        data = BlobETL(data, separator='.').to_dict()
        return TomlETL(data)

    def search(self, regex):
        # type: (str) -> TomlETL
        '''
        Returns portion of data whose keys match a given regular expression.

        Args:
            regex (str): Regular expression applied to keys.

        Returns:
            TomlETL: New TomlETL instance.
        '''
        data = BlobETL(self._data, separator='.') \
            .query(regex, ignore_case=False) \
            .to_dict()
        return TomlETL(data)
