import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import DataFrame
import radon.complexity
from radon.cli import Config
from radon.cli import CCHarvester, HCHarvester, MIHarvester, RawHarvester

from rolling_pin.blob_etl import BlobETL
# ------------------------------------------------------------------------------

'''
Contain the RadonETL class, which is used for generating a radon report on the
code wthin a given directory.
'''


class RadonETL():
    '''
    Conforms all four radon reports (raw metrics, Halstead, maintainability and
    cyclomatic complexity) into a single DataFrame that can then be plotted.
    '''
    def __init__(self, fullpath):
        '''
        Constructs a RadonETL instance.

        Args:
            fullpath (str or Path): Python file or directory of python files.
        '''
        self._report = RadonETL._get_radon_report(fullpath)
    # --------------------------------------------------------------------------

    @property
    def report(self):
        '''
        dict: Dictionary of all radon metrics.
        '''
        return self._report

    @property
    def data(self):
        '''
        pandas.DataFrame: DataFrame of all radon metrics.
        '''
        return self._get_radon_data()

    @property
    def raw_metrics(self):
        '''
        pandas.DataFrame: DataFrame of radon raw metrics.
        '''
        return self._get_raw_metrics_dataframe(self._report)

    @property
    def maintainability_index(self):
        '''
        pandas.DataFrame: DataFrame of radon maintainability index metrics.
        '''
        return self._get_maintainability_index_dataframe(self._report)

    @property
    def cyclomatic_complexity_metrics(self):
        '''
        pandas.DataFrame: DataFrame of radon cyclomatic complexity metrics.
        '''
        return self._get_cyclomatic_complexity_dataframe(self._report)

    @property
    def halstead_metrics(self):
        '''
        pandas.DataFrame: DataFrame of radon Halstead metrics.
        '''
        return self._get_halstead_dataframe(self._report)
    # --------------------------------------------------------------------------

    def _get_radon_data(self):
        '''
        Constructs a DataFrame representing all the radon reports generated for
        a given python file or directory containing python files.

        Returns:
            pandas.DataFrame: Radon report DataFrame.
        '''
        hal = self.halstead_metrics
        cc = self.cyclomatic_complexity_metrics
        raw = self.raw_metrics
        mi = self.maintainability_index

        data = hal.merge(cc, how='outer', on=['fullpath', 'name'])
        data['object_type'] = data.object_type_x
        mask = data.object_type_x.apply(pd.isnull)
        mask = data[mask].index
        data.loc[mask, 'object_type'] = data.loc[mask, 'object_type_y']
        del data['object_type_x']
        del data['object_type_y']

        module = raw.merge(mi, on='fullpath')

        cols = set(module.columns.tolist())
        cols = cols.difference(data.columns.tolist())
        cols = list(cols)
        for col in cols:
            data[col] = np.nan

        mask = data.object_type == 'module'
        for i, row in data[mask].iterrows():
            for col in cols:
                val = module[module.fullpath == row.fullpath][col].item()
                data.loc[i, col] = val

        cols = [
            'fullpath', 'name', 'class_name', 'object_type', 'blank', 'bugs',
            'calculated_length', 'code', 'column_offset', 'comment',
            'complexity', 'difficulty', 'effort', 'h1', 'h2', 'length',
            'logical_code', 'maintainability_index', 'maintainability_rank',
            'multiline_comment', 'n1', 'n2', 'rank', 'single_comment',
            'source_code', 'start_line', 'stop_line', 'time', 'vocabulary',
            'volume',
        ]
        data = data[cols]

        return data
    # --------------------------------------------------------------------------

    @staticmethod
    def _get_radon_report(fullpath):
        '''
        Gets all 4 report from radon and aggregates them into a single blob
        object.

        Args:
            fullpath (str or Path): Python file or directory of python files.

        Returns:
            dict: Radon report blob.
        '''
        if isinstance(fullpath, Path):
            fullpath = fullpath.absolute().as_posix()

        fullpath = [fullpath]
        output = []

        config = Config(
            min='A',
            max='F',
            exclude=None,
            ignore=None,
            show_complexity=False,
            average=False,
            total_average=False,
            order=getattr(
                radon.complexity, 'SCORE', getattr(radon.complexity, 'SCORE')
            ),
            no_assert=False,
            show_closures=False,
        )
        output.append(CCHarvester(fullpath, config).as_json())

        config = Config(
            exclude=None,
            ignore=None,
            summary=False,
        )
        output.append(RawHarvester(fullpath, config).as_json())

        config = Config(
            min='A',
            max='C',
            exclude=None,
            ignore=None,
            multi=True,
            show=False,
            sort=False,
        )
        output.append(MIHarvester(fullpath, config).as_json())

        config = Config(
            exclude=None,
            ignore=None,
            by_function=False,
        )
        output.append(HCHarvester(fullpath, config).as_json())

        output = list(map(json.loads, output))
        keys = [
            'cyclomatic_complexity', 'raw_metrics', 'maintainability_index',
            'halstead',
        ]
        output = dict(zip(keys, output))
        return output

    @staticmethod
    def _get_raw_metrics_dataframe(report):
        '''
        Converts radon raw metrics report into a pandas DataFrame.

        Args:
            report (dict): Radon report blob.

        Returns:
            pandas.DataFrame: Raw metrics DataFrame.
        '''
        raw = report['raw_metrics']
        fullpaths = list(raw.keys())
        path_lut = {k: f'<list_{i}>' for i, k in enumerate(fullpaths)}
        fullpath_fields = {x: {'fullpath': x} for x in fullpaths}

        #   loc = Lines of Code (total lines) - sloc + blanks + multi + single_comments
        #   lloc = Logical Lines of Code
        #   comments = Comments lines
        #   multi = Multi-line strings (assumed to be docstrings)
        #   blank = Blank lines (or whitespace-only lines)
        #   single_comments = Single-line comments or docstrings
        name_lut = dict(
            blank='blank',
            comments='comment',
            lloc='logical_code',
            loc='code',
            multi='multiline_comment',
            single_comments='single_comment',
            sloc='source_code',
            fullpath='fullpath',
        )
        data = BlobETL(raw, '#')\
            .update(fullpath_fields) \
            .set_field(0, lambda x: path_lut[x])\
            .set_field(1, lambda x: name_lut[x])\
            .to_dict()

        data = DataFrame(data)
        data.sort_values('fullpath', inplace=True)
        data.reset_index(drop=True, inplace=True)
        cols = [
            'fullpath', 'blank', 'code', 'comment', 'logical_code',
            'multiline_comment', 'single_comment', 'source_code',
        ]
        data = data[cols]

        return data

    @staticmethod
    def _get_maintainability_index_dataframe(report):
        '''
        Converts radon maintainability index report into a pandas DataFrame.

        Args:
            report (dict): Radon report blob.

        Returns:
            pandas.DataFrame: Maintainability DataFrame.
        '''
        mi = report['maintainability_index']
        fullpaths = list(mi.keys())
        path_lut = {k: f'<list_{i}>' for i, k in enumerate(fullpaths)}
        fullpath_fields = {x: {'fullpath': x} for x in fullpaths}
        name_lut = dict(
            mi='maintainability_index',
            rank='maintainability_rank',
            fullpath='fullpath',
        )
        data = BlobETL(mi, '#')\
            .update(fullpath_fields) \
            .set_field(0, lambda x: path_lut[x])\
            .set_field(1, lambda x: name_lut[x])\
            .to_dict()

        data = DataFrame(data)
        data.sort_values('fullpath', inplace=True)
        data.reset_index(drop=True, inplace=True)
        cols = ['fullpath', 'maintainability_index', 'maintainability_rank']
        data = data[cols]

        return data

    @staticmethod
    def _get_cyclomatic_complexity_dataframe(report):
        '''
        Converts radon cyclomatic complexity report into a pandas DataFrame.

        Args:
            report (dict): Radon report blob.

        Returns:
            pandas.DataFrame: Cyclomatic complexity DataFrame.
        '''
        lut = {
            'classname': 'class_name',
            'closures': 'closures',
            'col_offset': 'column_offset',
            'complexity': 'complexity',
            'endline': 'stop_line',
            'lineno': 'start_line',
            'name': 'name',
            'rank': 'rank',
            'type': 'object_type',
            'descriptor': 'descriptor',
            'fullpath': 'fullpath',
        }
        filters = [
            [4, 6, 'method_closure',
                '^[^#]+#<list_[0-9]+>#methods#<list_[0-9]+>#closures#<list_[0-9]+>#[^#]+$'],
            [3, 4, 'closure', '^[^#]+#<list_[0-9]+>#closures#<list_[0-9]+>#[^#]+$'],
            [3, 4, 'method', '^[^#]+#<list_[0-9]+>#methods#<list_[0-9]+>#[^#]+$'],
            [2, 2, None, '^[^#]+#<list_[0-9]+>#[^#]+$'],
        ]

        cc = report['cyclomatic_complexity']
        data = DataFrame()
        for i, j, type_, regex in filters:
            temp = BlobETL(cc, '#').query(regex)
            if len(temp.to_flat_dict().keys()) > 0:
                temp = temp.to_dataframe(i)
                item = temp\
                    .apply(lambda x: dict(zip(x[j], x['value'])), axis=1)\
                    .tolist()
                item = DataFrame(item)
                item['fullpath'] = temp[0]
                if type_ is not None:
                    item.type = type_
                data = data.append(item, ignore_index=True, sort=False)

        cols = [
            'fullpath', 'name', 'classname', 'type', 'complexity', 'rank',
            'lineno', 'endline', 'col_offset'
        ]
        data = data[cols]
        lut = {
            'fullpath': 'fullpath',
            'name': 'name',
            'classname': 'class_name',
            'type': 'object_type',
            'complexity': 'complexity',
            'rank': 'rank',
            'lineno': 'start_line',
            'endline': 'stop_line',
            'col_offset': 'column_offset',
        }
        data.drop_duplicates(inplace=True)
        data.rename(mapper=lambda x: lut[x], axis=1, inplace=True)
        data.reset_index(drop=True, inplace=True)

        return data

    @staticmethod
    def _get_halstead_dataframe(report):
        '''
        Converts radon Halstead report into a pandas DataFrame.

        Args:
            report (dict): Radon report blob.

        Returns:
            pandas.DataFrame: Halstead DataFrame.
        '''
        hal = report['halstead']
        keys = [
            'h1', 'h2', 'n1', 'n2', 'vocabulary', 'length', 'calculated_length',
            'volume', 'difficulty', 'effort', 'time', 'bugs',
        ]
        data = BlobETL(hal, '#').query('function|closure').to_dataframe(3)
        data['fullpath'] = data[0]
        data['object_type'] = data[1].apply(lambda x: re.sub('s$', '', x))
        data['name'] = data.value.apply(lambda x: x[0])

        score = data.value.apply(lambda x: dict(zip(keys, x[1:]))).tolist()
        score = DataFrame(score)
        data = data.join(score)

        total = BlobETL(hal, '#').query('total').to_dataframe()
        total['fullpath'] = total[0]
        total = total.groupby('fullpath', as_index=False)\
            .agg(lambda x: dict(zip(keys, x)))
        score = total.value.tolist()
        score = DataFrame(score)
        total = total.join(score)
        total['object_type'] = 'module'
        total['name'] = total.fullpath\
            .apply(lambda x: os.path.splitext((Path(x).name))[0])
        data = data.append(total, sort=False)

        cols = ['fullpath', 'name', 'object_type']
        cols.extend(keys)
        data = data[cols]

        return data
