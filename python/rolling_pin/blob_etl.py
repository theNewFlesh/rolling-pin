import json
import os
import re
from copy import deepcopy
from pathlib import Path

import networkx
import rolling_pin.tools as tools
# ------------------------------------------------------------------------------

'''
Contains the BlobETL class, which is used for coverting JSON blobs, and their
python equivalents, into flat dictionaries that can easily be modified and
converted to directed graphs.
'''


class BlobETL():
    '''
    Converts blob data internally into a flat dictionary that is universally
    searchable, editable and convertable back to the data's original structure,
    new blob structures or dircted graphs.
    '''
    def __init__(self, blob, separator='/'):
        '''
        Contructs BlobETL instance.

        Args:
            blob (object): Iterable object.
            separator (str, optional): String to be used as a field separator in
                each key. Default: '/'.
        '''
        self._data = tools.flatten(blob, separator=separator, embed_types=True)
        self._separator = separator

    def to_dict(self):
        '''
        Returns:
            dict: Nested representation of internal data.
        '''
        return tools.unembed(tools.nest(deepcopy(self._data)))

    def to_flat_dict(self):
        '''
        Returns:
            dict: Flat dictionary with embedded types.
        '''
        return deepcopy(self._data)

    def filter(self, predicate, by='key'):
        '''
        Filter data items by key, value or key + value, according to a given
        predicate.

        Args:
            predicate: Function that returns a boolean value.
            by (str, optional): Value handed to predicate.
                Options include: key, value, key+value. Default: key.

        Raises:
            ValueError: If by keyword is not key, value, or key+value.

        Returns:
            BlobETL: New BlobETL instance.
        '''
        data = {}
        if by not in ['key', 'value', 'key+value']:
            msg = f'Invalid by argument: {by}. Needs to be one of: '
            msg += 'key, value, key+value.'
            raise ValueError(msg)

        for key, val in self._data.items():
            item = None
            if by == 'key':
                item = [key]
            elif by == 'value':
                item = [val]
            else:
                item = [key, val]

            if predicate(*item):
                data[key] = val

        return BlobETL(data, self._separator)

    def delete(self, predicate, by='key'):
        '''
        Delete data items by key, value or key + value, according to a given
        predicate.

        Args:
            predicate: Function that returns a boolean value.
            by (str, optional): Value handed to predicate.
                Options include: key, value, key+value. Default: key.

        Raises:
            ValueError: If by keyword is not key, value, or key+value.

        Returns:
            BlobETL: New BlobETL instance.
        '''
        data = deepcopy(self._data)
        if by not in ['key', 'value', 'key+value']:
            msg = f'Invalid by argument: {by}. Needs to be one of: '
            msg += 'key, value, key+value.'
            raise ValueError(msg)

        for key, val in self._data.items():
            item = None
            if by == 'key':
                item = [key]
            elif by == 'value':
                item = [val]
            else:
                item = [key, val]

            if predicate(*item):
                del data[key]

        return BlobETL(data, self._separator)

    def set(
        self,
        predicate=None,
        key_setter=None,
        value_setter=None,
        by='key'
    ):
        '''
        Filter data items by key, value or key + value, according to a given
        predicate. Then set that items key by a given function and value by a
        given function.

        Args:
            predicate (function, optional): Function that returns a boolean
                value. Can be of form lambda k: bool or lambda k,v: bool.
                Default: None --> lambda k: True.
            key_setter (function, optional): Funciton of the form: lambda k: k.
                Default: None --> lambda k: k.
            value_setter (function, optional): Funciton of the form:
                lambda v: v. Default: None --> lambda v: v.
            by (str, optional): Value handed to predicate.
                Options include: key, value, key+value. Default: key.

        Raises:
            ValueError: If by keyword is not key, value, or key+value.

        Returns:
            BlobETL: New BlobETL instance.
        '''
        if by not in ['key', 'value', 'key+value']:
            msg = f'Invalid by argument: {by}. Needs to be one of: '
            msg += 'key, value, key+value.'
            raise ValueError(msg)

        # assign default predicate
        if predicate is None:
            predicate = lambda x: True

        # assign default key_setter
        if key_setter is None:
            key_setter = lambda x: x

        # assign default value_setter
        if value_setter is None:
            value_setter = lambda x: x

        data = deepcopy(self._data)
        for key, val in self._data.items():
            item = None
            if by == 'key':
                item = [key]
            elif by == 'value':
                item = [val]
            else:
                item = [key, val]

            if predicate(*item):
                k = key_setter(key)
                v = value_setter(val)
                del data[key]
                data[k] = v

        return BlobETL(data, self._separator)

    def update(self, item):
        '''
        Updates internal dictionary with given dictionary or BlobETL instance.
        Given dictionary is first flattened with embeded types.

        Args:
            item (dict or BlobETL): Dictionary to be used for update.

        Returns:
            BlobETL: New BlobETL instance.
        '''
        if isinstance(item, BlobETL):
            item = item._data
        temp = tools.flatten(item, separator=self._separator, embed_types=True)
        data = deepcopy(self._data)
        data.update(temp)
        return BlobETL(data, self._separator)

    def to_networkx_graph(self):
        '''
        Converts internal dictionar into a networkx directed graph.

        Returns:
            networkx.DiGraph: Graph representation of dictionary.
        '''
        graph = networkx.DiGraph()
        graph.add_node('root')
        embed_re = re.compile(r'<[a-z]+_(\d+)>')

        def recurse(item, parent):
            for key, val in item.items():
                k = f'{parent}{self._separator}{key}'
                short_name = embed_re.sub('\\1', key)
                graph.add_node(k, short_name=short_name, node_type='key')
                graph.add_edge(parent, k)

                if isinstance(val, dict):
                    recurse(val, k)
                else:
                    graph.nodes[k]['value'] = [val]
                    name = f'"{str(val)}"'
                    v = f'"{k}{self._separator}{str(val)}"'
                    graph.add_node(
                        v, short_name=name, node_type='value', value=[val]
                    )
                    graph.add_edge(k, v)

        recurse(tools.nest(self._data), 'root')
        graph.remove_node('root')
        return graph

    def to_dot_graph(self, orthogonal_edges=False, color_scheme=None):
        '''
        Converts internal dictionary into pydot graph.
        Key and value nodes and edges are colored differently.

        Args:
            orthogonal_edges (bool, optional): Whether graph edges should have
                non-right angles. Default: False.
            color_scheme: (dict, optional): Color scheme to be applied to graph.
                Default: rolling_pin.tools.COLOR_SCHEME

        Returns:
            pydot.Dot: Dot graph representation of dictionary.
        '''
        # set default colort scheme
        if color_scheme is None:
            color_scheme = tools.COLOR_SCHEME

        # create pydot graph
        graph = self.to_networkx_graph()
        dot = networkx.drawing.nx_pydot.to_pydot(graph)

        # set graph background color
        dot.set_bgcolor(color_scheme['background'])

        # set edge draw type
        if orthogonal_edges:
            dot.set_splines('ortho')

        # set draw parameters for each node of graph
        for node in dot.get_nodes():
            node.set_shape('rect')
            node.set_style('filled')
            node.set_color(color_scheme['node'])
            node.set_fillcolor(color_scheme['node'])
            node.set_fontcolor(color_scheme['node_font'])
            node.set_fontname('Courier')

            # if node has short name, set its displayed name to that
            attrs = node.get_attributes()
            if 'short_name' in attrs:
                node.set_label(attrs['short_name'])

            # if node type is value change its colors
            if 'node_type' in attrs and attrs['node_type'] == 'value':
                node.set_color(color_scheme['node_value'])
                node.set_fillcolor(color_scheme['node_value'])
                node.set_fontcolor(color_scheme['node_value_font'])

        # set draw parameters for each edge in graph
        for edge in dot.get_edges():
            edge.set_color(color_scheme['edge'])

            # if edge destination node type is value change its color
            node = dot.get_node(edge.get_destination())[0]
            attrs = node.get_attributes()
            if 'node_type' in attrs and attrs['node_type'] == 'value':
                edge.set_color(color_scheme['edge_value'])

        return dot

    def to_html(
        self,
        layout='dot',
        orthogonal_edges=False,
        color_scheme=None,
        as_png=False,
    ):
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
        orthogonal_edges=False,
        color_scheme=None
    ):
        '''
        Writes internal dictionary to a given filepath.
        Formats supported: svg, dot, png, json.

        Args:
            fulllpath (str or Path): File tobe written to.
            layout (str, optional): Graph layout style.
                Options include: circo, dot, fdp, neato, sfdp, twopi. Default: dot.

        Raises:
            ValueError: If invalid file extension given.
        '''
        if isinstance(fullpath, Path):
            fullpath = fullpath.absolute().as_posix()

        _, ext = os.path.splitext(fullpath)
        ext = re.sub(r'^\.', '', ext)
        if re.search('^json$', ext, re.I):
            with open(fullpath, 'w') as f:
                json.dump(self.to_dict(), f)
            return self

        if color_scheme is None:
            color_scheme = tools.COLOR_SCHEME

        graph = self.to_dot_graph(
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
