from typing import Dict, List, Union
from IPython.display import HTML, Image

from copy import deepcopy
from itertools import chain
from pathlib import Path
import re

from lunchbox.enforce import Enforce
from pandas import DataFrame
import yaml

from rolling_pin.blob_etl import BlobETL
from rolling_pin.conform_config import ConformConfig
import rolling_pin.tools as rpt

Rules = List[Dict[str, str]]
# ------------------------------------------------------------------------------


CONFORM_COLOR_SCHEME = deepcopy(rpt.COLOR_SCHEME)
CONFORM_COLOR_SCHEME.update({
    'node_font': '#DE958E',
    'node_value_font': '#B6ECF3',
    'edge': '#DE958E',
    'edge_value': '#B6ECF3',
    'node_library_font': '#B6ECF3',
    'node_module_font': '#DE958E',
    'edge_library': '#B6ECF3',
    'edge_module': '#DE958E'
})


class ConformETL:
    '''
    ConformETL creates a DataFrame from a given directory of source files.
    Then it generates target paths given a set of rules.
    Finally, the conform method is called and the source files are copied to
    their target filepaths.
    '''
    @staticmethod
    def _get_data(
        source_rules=[], rename_rules=[], group_rules=[], line_rules=[]
    ):
        # type: (Rules, Rules, Rules, Rules) -> DataFrame
        '''
        Generates DataFrame from given source_rules and then generates target
        paths for them given other rules.

        Args:
            source_rules (Rules): A list of rules for parsing directories.
                 Default: [].
            rename_rules (Rules): A list of rules for renaming source filepath
                to target filepaths. Default: [].
            group_rules (Rules): A list of rules for grouping files.
                Default: [].
            line_rules (Rules): A list of rules for peforming line copies on
                files belonging to a given group. Default: [].

        Returns:
            DataFrame: Conform DataFrame.
        '''
        # source
        source = []
        for rule in source_rules:
            files = rpt.list_all_files(
                rule['path'],
                include_regex=rule.get('include', None),
                exclude_regex=rule.get('exclude', None),
            )
            source.extend(files)
        source = sorted([x.as_posix() for x in source])
        data = DataFrame()
        data['source'] = source
        data['target'] = source

        # rename
        for rule in rename_rules:
            data.target = data.target \
                .apply(lambda x: re.sub(rule['regex'], rule['replace'], x))

        # group
        data['groups'] = data.source.apply(lambda x: [])
        for rule in group_rules:
            mask = data.source \
                .apply(lambda x: re.search(rule['regex'], x)) \
                .astype(bool)
            data.loc[mask, 'groups'] = data.groups \
                .apply(lambda x: x + [rule['name']])
        mask = data.groups.apply(lambda x: x == [])
        data.loc[mask, 'groups'] = data.loc[mask, 'groups'] \
            .apply(lambda x: ['base'])

        # line
        groups = set([x['group'] for x in line_rules])
        data['line_rule'] = data.groups \
            .apply(lambda x: len(set(x).intersection(groups)) > 0)

        return data

    @classmethod
    def from_yaml(cls, filepath):
        # type: (Union[str, Path]) -> ConformETL
        '''
        Construct ConformETL instance from given yaml file.

        Args:
            filepath (str or Path): YAML file.

        Raises:
            EnforceError: If file does not end in yml or yaml.

        Returns:
            ConformETL: ConformETL instance.
        '''
        filepath = Path(filepath).as_posix()
        ext = Path(filepath).suffix[1:].lower()
        msg = f'{filepath} does not end in yml or yaml.'
        Enforce(ext, 'in', ['yml', 'yaml'], message=msg)
        # ----------------------------------------------------------------------

        with open(filepath) as f:
            config = yaml.safe_load(f)
        return cls(**config)

    def __init__(
        self, source_rules=[], rename_rules=[], group_rules=[], line_rules=[]
    ):
        # type: (Rules, Rules, Rules, Rules) -> None
        '''
        Generates DataFrame from given source_rules and then generates target
        paths for them given other rules.

        Args:
            source_rules (Rules): A list of rules for parsing directories.
                 Default: [].
            rename_rules (Rules): A list of rules for renaming source filepath
                to target filepaths. Default: [].
            group_rules (Rules): A list of rules for grouping files.
                Default: [].
            line_rules (Rules): A list of rules for peforming line copies on
                files belonging to a given group. Default: [].

        Raises:
            DataError: If configuration is invalid.
        '''
        config = dict(
            source_rules=source_rules,
            rename_rules=rename_rules,
            group_rules=group_rules,
            line_rules=line_rules,
        )
        cfg = ConformConfig(config)
        cfg.validate()
        config = cfg.to_native()

        self._data = self._get_data(
            source_rules=source_rules,
            rename_rules=rename_rules,
            group_rules=group_rules,
            line_rules=line_rules,
        )  # type: DataFrame
        self._line_rules = line_rules  # type: Rules

    def __repr__(self):
        # type: () -> str
        '''
        String representation of conform DataFrame.

        Returns:
            str: Table optimized for output to shell.
        '''
        data = self._data.copy()
        data.line_rule = data.line_rule.apply(lambda x: 'X' if x else '')
        data.rename(lambda x: x.upper(), axis=1, inplace=True)
        output = data \
            .to_string(index=False, max_colwidth=150, col_space=[50, 50, 20, 10])
        return output

    @property
    def groups(self):
        # type: () -> List[str]
        '''
        list[str]: List of groups found with self._data.
        '''
        output = self._data.groups.tolist()
        output = sorted(list(set(chain(*output))))
        output.remove('base')
        output.insert(0, 'base')
        return output

    def to_dataframe(self):
        # type: () -> DataFrame
        '''
        Returns:
            DataFrame: Copy of internal data.
        '''
        return self._data.copy()

    def to_blob(self):
        # type: () -> BlobETL
        '''
        Converts self into a BlobETL object with target column as keys and
        source columns as values.

        Returns:
            BlobETL: BlobETL of target and source filepaths.
        '''
        data = self._data
        keys = data.target.tolist()
        vals = data.source.tolist()
        output = dict(zip(keys, vals))
        output = BlobETL(output)
        return output

    def to_html(
        self, orient='lr', color_scheme=CONFORM_COLOR_SCHEME, as_png=False
    ):
        # type: (str, Dict[str, str], bool) -> Union[Image, HTML]
        '''
        For use in inline rendering of graph data in Jupyter Lab.
        Graph from target to source filepath. Target is in red, source is in
        cyan.

        Args:
            orient (str, optional): Graph layout orientation. Default: lr.
                Options include:

                * tb - top to bottom
                * bt - bottom to top
                * lr - left to right
                * rl - right to left
            color_scheme: (dict, optional): Color scheme to be applied to graph.
                Default: rolling_pin.conform_etl.CONFORM_COLOR_SCHEME
            as_png (bool, optional): Display graph as a PNG image instead of
                SVG. Useful for display on Github. Default: False.

        Returns:
            IPython.display.HTML: HTML object for inline display.
        '''
        return self.to_blob() \
            .to_html(orient=orient, color_scheme=color_scheme, as_png=as_png)

    def conform(self, groups='all'):
        # type: (Union[str, List[str]]) -> None
        '''
        Copies source files to target filepaths.

        Args:
            groups (str or list[str]): Groups of files which are to be conformed.
                'all' means all groups. Default: 'all'.
        '''
        if isinstance(groups, str):
            if groups == 'all':
                groups = self.groups
            else:
                groups = [groups]

        data = self.to_dataframe()

        # copy files
        grps = set(groups)
        mask = data.groups \
            .apply(lambda x: set(x).intersection(grps)) \
            .apply(lambda x: len(x) > 0)
        data = data[mask]
        data.apply(lambda x: rpt.copy_file(x.source, x.target), axis=1)

        # copy lines
        data['text'] = data.source.apply(rpt.read_text)
        rules = list(filter(lambda x: x['group'] in groups, self._line_rules))
        for rule in rules:
            mask = data.groups.apply(lambda x: rule['group'] in x)
            data.loc[mask, 'text'] = data.loc[mask, 'text'].apply(
                lambda x: rpt.filter_text(
                    x,
                    include_regex=rule.get('include', None),
                    exclude_regex=rule.get('exclude', None),
                    replace_regex=rule.get('regex', None),
                    replace_value=rule.get('replace', None),
                )
            )
        data.apply(lambda x: rpt.write_text(x.text, x.target), axis=1)
