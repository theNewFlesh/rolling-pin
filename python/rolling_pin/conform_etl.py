from typing import Dict, List, Union
from IPython.display import HTML, Image

from copy import deepcopy
from itertools import chain
import re

from pandas import DataFrame

from rolling_pin.blob_etl import BlobETL
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
        '''
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

        for rule in rename_rules:
            data.target = data.target \
                .apply(lambda x: re.sub(rule['regex'], rule['replace'], x))

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

        self._data = data
        self._line_rules = line_rules

    def __repr__(self):
        # type: () -> str
        '''
        String representation of conform DataFrame.

        Returns:
            str: Table optimized for output to shell.
        '''
        return self._data \
            .rename(lambda x: x.upper(), axis=1) \
            .to_string(index=False, max_colwidth=150, col_space=[50, 50, 20])

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
        output = self._data
        keys = output.target.tolist()
        vals = output.source.tolist()
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

        data = self._data
        grps = set(groups)
        mask = data.groups \
            .apply(lambda x: set(x).intersection(grps)) \
            .apply(lambda x: len(x) > 0)
        data = data[mask]
        data.apply(lambda x: rpt.copy_file(x.source, x.target), axis=1)

        for rule in self._line_rules:
            mask = data.groups.apply(lambda x: rule['group'] in x)
            temp = data[mask]
            temp.apply(
                lambda x: rpt.copy_lines(
                    x.source,
                    x.target,
                    include_regex=rule.get('include', None),
                    exclude_regex=rule.get('exclude', None),
                ),
                axis=1
            )