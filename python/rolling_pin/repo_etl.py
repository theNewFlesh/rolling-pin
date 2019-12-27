from itertools import chain
import re

import networkx
import numpy as np
from pandas import DataFrame, Series

import rolling_pin.tools as tools
# ------------------------------------------------------------------------------


def get_imports(fullpath):
    '''
    Get's import statements from a given python module.

    Args:
        fullpath (str or Path): Path to python module.

    Returns:
        list(str): List of imported modules.
    '''
    with open(fullpath) as f:
        data = f.readlines()
    data = map(lambda x: x.strip('\n'), data)
    data = filter(lambda x: re.search('^import|^from', x), data)
    data = map(lambda x: re.sub('from (.*?) .*', '\\1', x), data)
    data = map(lambda x: re.sub(' as .*', '', x), data)
    data = map(lambda x: re.sub(' *#.*', '', x), data)
    data = map(lambda x: re.sub('import ', '', x), data)
    data = filter(lambda x: not is_builtin(x), data)
    return list(data)


def is_builtin(module):
    '''
    Determines if given module is a python builtin.

    Args:
        module (str): Python module name.

    Returns:
        bool: Whether string names a python module.
    '''
    builtins = [
        'copy',
        'datetime',
        'enum',
        'functools',
        'inspect',
        'itertools',
        'json',
        'logging',
        'math',
        'os',
        'pathlib',
        're',
        'uuid'
    ]
    suffix = r'(\..*)?'
    builtins_re = f'{suffix}|'.join(builtins) + suffix
    if re.search(builtins_re, module):
        return True
    return False


class RepoETL():
    def __init__(
        self,
        source,
        include_regex=r'.*\.py$',
        exclude_regex=r'(__init__|_test)\.py$',
    ):
        self._source = source
        self._data = self._get_data(source, include_regex, exclude_regex)

    def _get_data(self, source, include_regex, exclude_regex):
        files = tools.list_all_files(source)
        if include_regex != '':
            if not include_regex.endswith(r'\.py$'):
                msg = r'include_regex does not end in "\.py$".'
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

        # buid DataFrame of nodes and imported dependencies
        data = DataFrame()
        data['fullpath'] = files
        data['node_name'] = data.fullpath\
            .apply(lambda x: x.absolute().as_posix())\
            .apply(lambda x: re.sub(source, '', x))\
            .apply(lambda x: re.sub(r'\.py$', '', x))\
            .apply(lambda x: re.sub('^/', '', x))\
            .apply(lambda x: re.sub('/', '.', x))

        data['subpackages'] = data.node_name\
            .apply(lambda x: tools.get_parent_fields(x, '.')).apply(tools.get_ordered_unique)
        data.subpackages = data.subpackages\
            .apply(lambda x: list(filter(lambda y: y != '', x)))

        data['dependencies'] = data.fullpath\
            .apply(get_imports).apply(tools.get_ordered_unique)
        data.dependencies += data.node_name\
            .apply(lambda x: ['.'.join(x.split('.')[:-1])])
        data.dependencies = data.dependencies\
            .apply(lambda x: list(filter(lambda y: y != '', x)))

        data['node_type'] = 'module'

        # add subpackages as nodes
        pkgs = set(chain(*data.subpackages.tolist()))
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
        libs = set(chain(*data.dependencies.tolist()))
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
        data = self._calculate_coordinates(data)
        data = self._anneal_coordinates(data)
        data = self._center_x_coordinates(data)

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

    def _calculate_coordinates(self, data, epochs=10):
        for item in ['module', 'subpackage', 'library']:
            mask = data.node_type == item
            n = data[mask].shape[0]

            index = data[mask].index
            data.loc[index, 'x'] = list(range(n))

            if item != 'library':
                data.loc[index, 'y'] = data.loc[index, 'node_name']\
                    .apply(lambda x: len(x.split('.')))

        max_ = data[data.node_type == 'subpackage'].y.max()
        index = data[data.node_type == 'module'].index
        data.loc[index, 'y'] += max_
        data.loc[index, 'y'] += data.loc[index, 'subpackages'].apply(len)

        # reverse y
        max_ = data.y.max()
        data.y = -1 * data.y + max_

        return data

    def _anneal_coordinates(self, data, epochs=10):
        for epoch in range(epochs):
            graph = self._to_networkx_graph(data)
            if epoch % 2 == 0:
                graph = graph.reverse()

            for name in graph.nodes:
                tree = networkx.bfs_tree(graph, name)
                mu_x = np.mean([graph.nodes[n]['x'] for n in tree])
                graph.nodes[name]['x'] = mu_x

            for node in graph.nodes:
                mask = data[data.node_name == node].index
                data.loc[mask, 'x'] = graph.nodes[node]['x']

            # rectify node x coordinates
            data.sort_values('x', inplace=True)
            for y in data.y.unique():
                mask = data[data.y == y].index
                values = data.loc[mask, 'x'].tolist()
                values = list(range(len(values)))
                data.loc[mask, 'x'] = values

        return data

    def _center_x_coordinates(self, data):
        max_ = data.x.max()
        for y in data.y.unique():
            mask = data[data.y == y].index
            l_max = data.loc[mask, 'x'].max()
            delta = max_ - l_max
            data.loc[mask, 'x'] += (delta / 2)
        return data

    def _to_networkx_graph(self, data):
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
        return self._to_networkx_graph(self._data)

    def to_dot_graph(self, orthogonal_edges=False, color_scheme=None):
        if color_scheme is None:
            color_scheme = tools.COLOR_SCHEME

        graph = self.to_networkx_graph()
        dot = networkx.drawing.nx_pydot.to_pydot(graph)
        if orthogonal_edges:
            dot.set_splines('ortho')
        dot.set_bgcolor(color_scheme['background'])

        for node in dot.get_nodes():
            gnode = re.sub('"', '', node.get_name())
            gnode = graph.nodes[gnode]
            if gnode == {}:
                continue

            node.set_pos(f"{gnode['x']},{gnode['y']}!")

            node.set_shape('rect')
            node.set_style('filled')
            node.set_color(color_scheme['node'])
            node.set_fillcolor(color_scheme['node'])
            node.set_fontname('Courier')

            if gnode['node_type'] == 'library':
                node.set_fontcolor(color_scheme['node_library_font'])
            elif gnode['node_type'] == 'subpackage':
                node.set_fontcolor(color_scheme['node_subpackage_font'])
            else:
                node.set_fontcolor(color_scheme['node_module_font'])

        for edge in dot.get_edges():
            gnode = dot.get_node(edge.get_source())
            gnode = gnode[0].get_name()
            gnode = re.sub('"', '', gnode)
            gnode = graph.nodes[gnode]
            if gnode == {}:
                continue

            if gnode['node_type'] == 'library':
                edge.set_color(color_scheme['edge_library'])
            elif gnode['node_type'] == 'subpackage':
                edge.set_color(color_scheme['edge_subpackage'])
            else:
                edge.set_color(color_scheme['edge_module'])

        return dot

    def to_dataframe(self):
        return self._data

    def to_html(self, layout='dot', orthogonal_edges=False, color_scheme=None):
        if color_scheme is None:
            color_scheme = tools.COLOR_SCHEME

        dot = self.to_dot_graph(
            orthogonal_edges=orthogonal_edges,
            color_scheme=color_scheme,
        )
        return tools.dot_to_html(dot, layout=layout)

    def write(
        self,
        fullpath,
        layout='dot',
        orthogonal_edges=False,
        color_scheme=None
    ):
        if color_scheme is None:
            color_scheme = tools.COLOR_SCHEME

        graph = self.to_dot_graph(
            orthogonal_edges=orthogonal_edges,
            color_scheme=color_scheme,
        )
        tools.write_dot_graph(graph, fullpath, layout=layout,)
        return self
