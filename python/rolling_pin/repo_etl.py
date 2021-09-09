from typing import Any, Dict, Iterator, List, Optional, Union

from itertools import chain
from pathlib import Path
import os
import re

from IPython.display import HTML
from pandas import DataFrame, Series
import lunchbox.tools as lbt
import networkx
import numpy as np

from rolling_pin.radon_etl import RadonETL
import rolling_pin.tools as tools
# ------------------------------------------------------------------------------

'''
Contains the RepoETL class, which is used for converted python repository module
dependencies into a directed graph.
'''


class RepoETL():
    '''
    RepoETL is a class for extracting 1st order dependencies of modules within a
    given repository. This information is stored internally as a DataFrame and
    can be rendered as networkx, pydot or SVG graphs.
    '''
    def __init__(
        self,
        root,
        include_regex=r'.*\.py$',
        exclude_regex=r'(__init__|test_|_test|mock_)\.py$',
    ):
        # type: (Union[str, Path], str, str) -> None
        r'''
        Construct RepoETL instance.

        Args:
            root (str or Path): Full path to repository root directory.
            include_regex (str, optional): Files to be included in recursive
                directy search. Default: '.*\.py$'.
            exclude_regex (str, optional): Files to be excluded in recursive
                directy search. Default: '(__init__|test_|_test|mock_)\.py$'.

        Raises:
            ValueError: If include or exclude regex does not end in '\.py$'.
        '''
        self._root = root  # type: Union[str, Path]
        self._data = self._get_data(root, include_regex, exclude_regex)  # type: DataFrame

    @staticmethod
    def _get_imports(fullpath):
        # type: (Union[str, Path]) -> List[str]
        '''
        Get's import statements from a given python module.

        Args:
            fullpath (str or Path): Path to python module.

        Returns:
            list(str): List of imported modules.
        '''
        with open(fullpath) as f:
            data = f.readlines()  # type: Union[List, Iterator]
        data = map(lambda x: x.strip('\n'), data)
        data = filter(lambda x: re.search('^import|^from', x), data)
        data = map(lambda x: re.sub('from (.*?) .*', '\\1', x), data)
        data = map(lambda x: re.sub(' as .*', '', x), data)
        data = map(lambda x: re.sub(' *#.*', '', x), data)
        data = map(lambda x: re.sub('import ', '', x), data)
        data = filter(lambda x: not lbt.is_standard_module(x), data)
        return list(data)

    @staticmethod
    def _get_data(
        root,
        include_regex=r'.*\.py$',
        exclude_regex=r'(__init__|_test)\.py$',
    ):
        # type: (Union[str, Path], str, str) -> DataFrame
        r'''
        Recursively aggregates and filters all the files found with a given
        directory into a DataFrame. Data is used to create directed graphs.

        DataFrame has these columns:

            * node_name    - name of node
            * node_type    - type of node, can be [module, subpackage, library]
            * x            - node's x coordinate
            * y            - node's y coordinate
            * dependencies - parent nodes
            * subpackages  - parent nodes of type subpackage
            * fullpath     - fullpath to the module a node represents

        Args:
            root (str or Path): Root directory to be searched.
            include_regex (str, optional): Files to be included in recursive
                directy search. Default: '.*\.py$'.
            exclude_regex (str, optional): Files to be excluded in recursive
                directy search. Default: '(__init__|_test)\.py$'.

        Raises:
            ValueError: If include or exclude regex does not end in '\.py$'.
            FileNotFoundError: If no files are found after filtering.

        Returns:
            DataFrame: DataFrame of file information.
        '''
        root = Path(root).as_posix()
        files = tools.list_all_files(root)  # type: Union[Iterator, List]
        if include_regex != '':
            if not include_regex.endswith(r'\.py$'):
                msg = f"Invalid include_regex: '{include_regex}'. "
                msg += r"Does not end in '.py$'."
                raise ValueError(msg)

            files = filter(
                lambda x: re.search(include_regex, x.absolute().as_posix()),
                files
            )
        if exclude_regex != '':
            files = filter(
                lambda x: not re.search(exclude_regex, x.absolute().as_posix()),
                files
            )

        files = list(files)
        if len(files) == 0:
            msg = f'No files found after filters in directory: {root}.'
            raise FileNotFoundError(msg)

        # buid DataFrame of nodes and imported dependencies
        data = DataFrame()
        data['fullpath'] = files
        data.fullpath = data.fullpath.apply(lambda x: x.absolute().as_posix())

        data['node_name'] = data.fullpath\
            .apply(lambda x: re.sub(root, '', x))\
            .apply(lambda x: re.sub(r'\.py$', '', x))\
            .apply(lambda x: re.sub('^/', '', x))\
            .apply(lambda x: re.sub('/', '.', x))

        data['subpackages'] = data.node_name\
            .apply(lambda x: tools.get_parent_fields(x, '.')).apply(lbt.get_ordered_unique)
        data.subpackages = data.subpackages\
            .apply(lambda x: list(filter(lambda y: y != '', x)))

        data['dependencies'] = data.fullpath\
            .apply(RepoETL._get_imports).apply(lbt.get_ordered_unique)
        data.dependencies += data.node_name\
            .apply(lambda x: ['.'.join(x.split('.')[:-1])])
        data.dependencies = data.dependencies\
            .apply(lambda x: list(filter(lambda y: y != '', x)))

        data['node_type'] = 'module'

        # add subpackages as nodes
        pkgs = set(chain(*data.subpackages.tolist()))  # type: Any
        pkgs = pkgs.difference(data.node_name.tolist())
        pkgs = sorted(list(pkgs))
        pkgs = Series(pkgs)\
            .apply(
                lambda x: dict(
                    node_name=x,
                    node_type='subpackage',
                    dependencies=tools.get_parent_fields(x, '.'),
                    subpackages=tools.get_parent_fields(x, '.'),
                )).tolist()
        pkgs = DataFrame(pkgs)
        data = data.append(pkgs, ignore_index=True, sort=True)

        # add library dependencies as nodes
        libs = set(chain(*data.dependencies.tolist()))  # type: Any
        libs = libs.difference(data.node_name.tolist())
        libs = sorted(list(libs))
        libs = Series(libs)\
            .apply(
                lambda x: dict(
                    node_name=x,
                    node_type='library',
                    dependencies=[],
                    subpackages=[],
                )).tolist()
        libs = DataFrame(libs)
        data = data.append(libs, ignore_index=True, sort=True)

        data.drop_duplicates('node_name', inplace=True)
        data.reset_index(drop=True, inplace=True)

        # define node coordinates
        data['x'] = 0
        data['y'] = 0
        data = RepoETL._calculate_coordinates(data)
        data = RepoETL._anneal_coordinate(data, 'x', 'y')
        data = RepoETL._center_coordinate(data, 'x', 'y')

        data.sort_values('fullpath', inplace=True)
        data.reset_index(drop=True, inplace=True)

        cols = [
            'node_name',
            'node_type',
            'x',
            'y',
            'dependencies',
            'subpackages',
            'fullpath',
        ]
        data = data[cols]
        return data

    @staticmethod
    def _calculate_coordinates(data):
        # type: (DataFrame) -> DataFrame
        '''
        Calculate inital x, y coordinates for each node in given DataFrame.
        Node are startified by type along the y axis.

        Args:
            DataFrame: DataFrame of nodes.

        Returns:
            DataFrame: DataFrame with x and y coordinate columns.
        '''
        # set initial node coordinates
        data['y'] = 0
        for item in ['module', 'subpackage', 'library']:
            mask = data.node_type == item
            n = data[mask].shape[0]

            index = data[mask].index
            data.loc[index, 'x'] = list(range(n))

            # move non-library nodes down the y axis according to how nested
            # they are
            if item != 'library':
                data.loc[index, 'y'] = data.loc[index, 'node_name']\
                    .apply(lambda x: len(x.split('.')))

        # move all module nodes beneath supackage nodes on the y axis
        max_ = data[data.node_type == 'subpackage'].y.max()
        index = data[data.node_type == 'module'].index
        data.loc[index, 'y'] += max_
        data.loc[index, 'y'] += data.loc[index, 'subpackages'].apply(len)

        # reverse y axis
        max_ = data.y.max()
        data.y = -1 * data.y + max_

        return data

    @staticmethod
    def _anneal_coordinate(data, anneal_axis='x', pin_axis='y', iterations=10):
        # type: (DataFrame, str, str, int) -> DataFrame
        '''
        Iteratively align nodes in the anneal axis according to the mean
        position of their connected nodes. Node anneal coordinates are rectified
        at the end of each iteration according to a pin axis, so that they do
        not overlap. This mean that they are sorted at each level of the pin
        axis.

        Args:
            data (DataFrame): DataFrame with x column.
            anneal_axis (str, optional): Coordinate column to be annealed.
                Default: 'x'.
            pin_axis (str, optional): Coordinate column to be held constant.
                Default: 'y'.
            iterations (int, optional): Number of times to update x coordinates.
                Default: 10.

        Returns:
            DataFrame: DataFrame with annealed anneal axis coordinates.
        '''
        x = anneal_axis
        y = pin_axis
        for iteration in range(iterations):
            # create directed graph from data
            graph = RepoETL._to_networkx_graph(data)

            # reverse connectivity every other iteration
            if iteration % 2 == 0:
                graph = graph.reverse()

            # get mean coordinate of each node in directed graph
            for name in graph.nodes:
                tree = networkx.bfs_tree(graph, name)
                mu = np.mean([graph.nodes[n][x] for n in tree])
                graph.nodes[name][x] = mu

            # update data coordinate column
            for node in graph.nodes:
                mask = data[data.node_name == node].index
                data.loc[mask, x] = graph.nodes[node][x]

            # rectify data coordinate column, so that no two nodes overlap
            data.sort_values(x, inplace=True)
            for yi in data[y].unique():
                mask = data[data[y] == yi].index
                values = data.loc[mask, x].tolist()
                values = list(range(len(values)))
                data.loc[mask, x] = values

        return data

    @staticmethod
    def _center_coordinate(data, center_axis='x', pin_axis='y'):
        # (DataFrame, str, str) -> DataFrame
        '''
        Sorted center_axis coordinates at each level of the pin axis.

        Args:
            data (DataFrame): DataFrame with x column.
            anneal_column (str, optional): Coordinate column to be annealed.
                Default: 'x'.
            pin_axis (str, optional): Coordinate column to be held constant.
                Default: 'y'.
            iterations (int, optional): Number of times to update x coordinates.
                Default: 10.

        Returns:
            DataFrame: DataFrame with centered center axis coordinates.
        '''
        x = center_axis
        y = pin_axis
        max_ = data[x].max()
        for yi in data[y].unique():
            mask = data[data[y] == yi].index
            l_max = data.loc[mask, x].max()
            delta = max_ - l_max
            data.loc[mask, x] += (delta / 2)
        return data

    @staticmethod
    def _to_networkx_graph(data):
        # (DataFrame) -> networkx.DiGraph
        '''
        Converts given DataFrame into networkx directed graph.

        Args:
            DataFrame: DataFrame of nodes.

        Returns:
            networkx.DiGraph: Graph of nodes.
        '''
        graph = networkx.DiGraph()
        data.apply(
            lambda x: graph.add_node(
                x.node_name,
                **{k: getattr(x, k) for k in x.index}
            ),
            axis=1
        )

        data.apply(
            lambda x: [graph.add_edge(p, x.node_name) for p in x.dependencies],
            axis=1
        )
        return graph

    def to_networkx_graph(self):
        # () -> networkx.DiGraph
        '''
        Converts internal data into networkx directed graph.

        Returns:
            networkx.DiGraph: Graph of nodes.
        '''
        return RepoETL._to_networkx_graph(self._data)

    def to_dot_graph(self, orient='tb', orthogonal_edges=False, color_scheme=None):
        # (str, bool, Optional[Dict[str, str]]) -> pydot.Dot
        '''
        Converts internal data into pydot graph.

        Args:
            orient (str, optional): Graph layout orientation. Default: tb.
                Options include:

                * tb - top to bottom
                * bt - bottom to top
                * lr - left to right
                * rl - right to left
            orthogonal_edges (bool, optional): Whether graph edges should have
                non-right angles. Default: False.
            color_scheme: (dict, optional): Color scheme to be applied to graph.
                Default: rolling_pin.tools.COLOR_SCHEME

        Raises:
            ValueError: If orient is invalid.

        Returns:
            pydot.Dot: Dot graph of nodes.
        '''
        orient = orient.lower()
        orientations = ['tb', 'bt', 'lr', 'rl']
        if orient not in orientations:
            msg = f'Invalid orient value. {orient} not in {orientations}.'
            raise ValueError(msg)

        # set color scheme of graph
        if color_scheme is None:
            color_scheme = tools.COLOR_SCHEME

        # create dot graph
        graph = self.to_networkx_graph()
        dot = networkx.drawing.nx_pydot.to_pydot(graph)

        # set layout orientation
        dot.set_rankdir(orient.upper())

        # set graph background color
        dot.set_bgcolor(color_scheme['background'])

        # set edge draw type
        if orthogonal_edges:
            dot.set_splines('ortho')

        # set draw parameters for each node in graph
        for node in dot.get_nodes():
            # set node shape, color and font attributes
            node.set_shape('rect')
            node.set_style('filled')
            node.set_color(color_scheme['node'])
            node.set_fillcolor(color_scheme['node'])
            node.set_fontname('Courier')

            nx_node = re.sub('"', '', node.get_name())
            nx_node = graph.nodes[nx_node]

            # if networkx node has no attributes skip it
            # this should not ever occur but might
            if nx_node == {}:
                continue  # pragma: no cover

            # set node x, y coordinates
            node.set_pos(f"{nx_node['x']},{nx_node['y']}!")

            # vary node font color by noe type
            if nx_node['node_type'] == 'library':
                node.set_fontcolor(color_scheme['node_library_font'])
            elif nx_node['node_type'] == 'subpackage':
                node.set_fontcolor(color_scheme['node_subpackage_font'])
            else:
                node.set_fontcolor(color_scheme['node_module_font'])

        # set draw parameters for each edge in graph
        for edge in dot.get_edges():
            # get networkx source node of edge
            nx_node = dot.get_node(edge.get_source())
            nx_node = nx_node[0].get_name()
            nx_node = re.sub('"', '', nx_node)
            nx_node = graph.nodes[nx_node]

            # if networkx source node has no attributes skip it
            # this should not ever occur but might
            if nx_node == {}:
                continue  # pragma: no cover

            # vary edge color by its source node type
            if nx_node['node_type'] == 'library':
                edge.set_color(color_scheme['edge_library'])
            elif nx_node['node_type'] == 'subpackage':
                edge.set_color(color_scheme['edge_subpackage'])
            else:
                # this line is actually covered by pytest doesn't think so
                edge.set_color(color_scheme['edge_module'])  # pragma: no cover

        return dot

    def to_dataframe(self):
        # type: () -> DataFrame
        '''
        Retruns:
            DataFrame: DataFrame of nodes representing repo modules.
        '''
        return self._data.copy()

    def to_html(
        self,
        layout='dot',
        orthogonal_edges=False,
        color_scheme=None,
        as_png=False
    ):
        # type: (str, bool, Optional[Dict[str, str]], bool) -> HTML
        '''
        For use in inline rendering of graph data in Jupyter Lab.

        Args:
            layout (str, optional): Graph layout style.
                Options include: circo, dot, fdp, neato, sfdp, twopi.
                Default: dot.
            orthogonal_edges (bool, optional): Whether graph edges should have
                non-right angles. Default: False.
            color_scheme: (dict, optional): Color scheme to be applied to graph.
                Default: rolling_pin.tools.COLOR_SCHEME
            as_png (bool, optional): Display graph as a PNG image instead of
                SVG. Useful for display on Github. Default: False.

        Returns:
            IPython.display.HTML: HTML object for inline display.
        '''
        if color_scheme is None:
            color_scheme = tools.COLOR_SCHEME

        dot = self.to_dot_graph(
            orthogonal_edges=orthogonal_edges,
            color_scheme=color_scheme,
        )
        return tools.dot_to_html(dot, layout=layout, as_png=as_png)

    def write(
        self,
        fullpath,
        layout='dot',
        orient='tb',
        orthogonal_edges=False,
        color_scheme=None
    ):
        # type: (Union[str, Path], str, str, bool, Optional[Dict[str, str]]) -> RepoETL
        '''
        Writes internal data to a given filepath.
        Formats supported: svg, dot, png, json.

        Args:
            fulllpath (str or Path): File to be written to.
            layout (str, optional): Graph layout style.
                Options include: circo, dot, fdp, neato, sfdp, twopi. Default: dot.
            orient (str, optional): Graph layout orientation. Default: tb.
                Options include:

                * tb - top to bottom
                * bt - bottom to top
                * lr - left to right
                * rl - right to left
            orthogonal_edges (bool, optional): Whether graph edges should have
                non-right angles. Default: False.
            color_scheme: (dict, optional): Color scheme to be applied to graph.
                Default: rolling_pin.tools.COLOR_SCHEME

        Raises:
            ValueError: If invalid file extension given.

        Returns:
            RepoETL: Self.
        '''
        if isinstance(fullpath, Path):
            fullpath = fullpath.absolute().as_posix()

        _, ext = os.path.splitext(fullpath)
        ext = re.sub(r'^\.', '', ext)
        if re.search('^json$', ext, re.I):
            self._data.to_json(fullpath, orient='records')
            return self

        if color_scheme is None:
            color_scheme = tools.COLOR_SCHEME

        graph = self.to_dot_graph(
            orient=orient,
            orthogonal_edges=orthogonal_edges,
            color_scheme=color_scheme,
        )
        try:
            tools.write_dot_graph(graph, fullpath, layout=layout,)
        except ValueError:
            msg = f'Invalid extension found: {ext}. '
            msg += 'Valid extensions include: svg, dot, png, json.'
            raise ValueError(msg)
        return self
# ------------------------------------------------------------------------------


def write_repo_architecture(
    source, target, exclude_regex='test|mock', orient='lr'
):
    # type: (Union[str, Path], Union[str, Path], str, str) -> None
    '''
    Convenience function for writing a repo architecture graph.

    Args:
        source (str or Path): Repo directory.
        target (str or Path): Target filepath.
        exclude_regex (str, optional): Exclude files that match this regex pattern.
            Default: 'test|mock'.
        orient (str, optional): Graph orientation. Default: lr.
    '''
    etl = RepoETL(source)
    data = etl._data.copy()
    func = lambda x: not bool(re.search(exclude_regex, x))
    mask = data.node_name.apply(func)
    data = data[mask]
    data.reset_index(inplace=True, drop=True)
    data.dependencies = data.dependencies.apply(lambda x: list(filter(func, x)))
    etl._data = data
    etl.write(target, orient=orient)


def write_repo_plots_and_tables(source, plot_path, table_dir):
    # type: (Union[str, Path], Union[str, Path], Union[str, Path]) -> None
    '''
    Convenience function for writing repo plot and table files.

    Args:
        source (str or Path): Repo directory.
        plot_path (str or Path): Plot filepath.
        table_dir (str or Path): Table parent directory.
    '''
    etl = RadonETL(source)
    etl.write_plots(plot_path)
    etl.write_tables(table_dir)
