from typing import Any, Type, TypeVar, Union  # noqa: F401

from copy import deepcopy
from pathlib import Path
import os

from lunchbox.enforce import Enforce
import toml

from rolling_pin.blob_etl import BlobETL
from toml.decoder import TomlDecodeError

T = TypeVar('T', bound='TomlETL')
# ------------------------------------------------------------------------------


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
        return toml.dumps(
            self._data, encoder=toml.TomlArraySeparatorEncoder(separator=',')
        )

    def write(self, filepath):
        # type: (Union[str, Path]) -> None
        '''
        Writes instance to given TOML file.

        Args:
            filepath (str or Path): Target filepath.
        '''
        filepath = Path(filepath)
        os.makedirs(filepath.parent, exist_ok=True)
        with open(filepath, 'w') as f:
            toml.dump(
                self._data,
                f,
                encoder=toml.TomlArraySeparatorEncoder(separator=',')
            )

    def edit(self, patch):
        # type: (str) -> TomlETL
        '''
        Apply edit to internal data given TOML patch.
        Patch is always of the form '[key]=[value]' and in TOML format.

        Args:
            patch (str): TOML patch to be applied.

        Raises:
            TOMLDecoderError: If patch cannot be decoded.
            EnforceError: If '=' not found in patch.

        Returns:
            TomlETL: New TomlETL instance with edits.
        '''
        msg = 'Edit patch must be a TOML parsable key value snippet with a "=" '
        msg += 'character.'
        try:
            toml.loads(patch)
        except TomlDecodeError as e:
            msg += ' ' + e.msg
            raise TomlDecodeError(msg, e.doc, e.pos)
        Enforce('=', 'in', patch, message=msg)
        # ----------------------------------------------------------------------

        key, val = patch.split('=', maxsplit=1)
        val = toml.loads(f'x={val}')['x']
        data = BlobETL(self._data, separator='.').to_flat_dict()
        data[key] = val
        data = BlobETL(data, separator='.').to_dict()
        return TomlETL(data)

    def delete(self, regex):
        # type: (str) -> TomlETL
        '''
        Returns portion of data whose keys fo not match a given regular expression.

        Args:
            regex (str): Regular expression applied to keys.

        Returns:
            TomlETL: New TomlETL instance.
        '''
        data = BlobETL(self._data, separator='.') \
            .query(regex, ignore_case=False, invert=True) \
            .to_dict()
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
