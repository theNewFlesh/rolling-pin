from typing import Dict, List

from pathlib import Path

from schematics import Model
from schematics.exceptions import ValidationError
from schematics.types import ListType, ModelType, StringType

Rules = List[Dict[str, str]]
# ------------------------------------------------------------------------------


def is_dir(dirpath):
    # type: (str) -> None
    '''
    Validates whether a given dirpath exists.

    Args:
        dirpath (str): Directory path.

    Raises:
        ValidationError: If dirpath is not a directory or does not exist.
    '''
    if not Path(dirpath).is_dir():
        msg = f'{dirpath} is not a directory or does not exist.'
        raise ValidationError(msg)


class ConformConfig(Model):
    '''
    A class for validating configurations supplied to ConformETL.

    Attributes:
        source_rules (Rules): A list of rules for parsing directories.
            Default: [].
        rename_rules (Rules): A list of rules for renaming source filepath
            to target filepaths. Default: [].
        group_rules (Rules): A list of rules for grouping files.
            Default: [].
        line_rules (Rules): A list of rules for peforming line copies and
            substitutions on files belonging to a given group. Default: [].
    '''
    class SourceRule(Model):
        path = StringType(required=True, validators=[is_dir])  # type: StringType
        include = StringType(required=False, serialize_when_none=False)  # type: StringType
        exclude = StringType(required=False, serialize_when_none=False)  # type: StringType

    class RenameRule(Model):
        regex = StringType(required=True)  # type: StringType
        replace = StringType(required=True)  # type: StringType

    class GroupRule(Model):
        name = StringType(required=True)  # type: StringType
        regex = StringType(required=True)  # type: StringType

    class LineRule(Model):
        group = StringType(required=True)  # type: StringType
        include = StringType(required=False, serialize_when_none=False)  # type: StringType
        exclude = StringType(required=False, serialize_when_none=False)  # type: StringType
        regex = StringType(required=False)  # type: StringType
        replace = StringType(required=False)  # type: StringType

    source_rules = ListType(ModelType(SourceRule), required=True)  # type: ListType
    rename_rules = ListType(ModelType(RenameRule), required=False)  # type: ListType
    group_rules = ListType(ModelType(GroupRule), required=False)  # type: ListType
    line_rules = ListType(ModelType(LineRule), required=False)  # type: ListType
