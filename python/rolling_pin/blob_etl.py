from copy import deepcopy
import re

import networkx

import rolling_pin.tools as tools
# ------------------------------------------------------------------------------


class BlobETL():
    def __init__(self, item, separator='/'):
        self._data = tools.flatten(item, separator=separator, embed_types=True)
        self._separator = separator

    def to_dict(self):
        return tools.unembed(tools.nest(self._data))

    def to_flat_dict(self):
        return self._data

    def filter(self, predicate, by='key'):
        data = {}
        if by not in ['key', 'value', 'key+value']:
            msg = f'Invalid by argument: {by}. Needs to be one of: '
            msg += 'key, value, key+value.'
            raise ValueError(msg)

        for key, val in self._data.items():
            item = None
            if by == 'key':
                item = key
            elif by == 'value':
                item = val
            else:
                item = [key, val]

            if predicate(item):
                data[key] = val

        self._data = data
        return self

    def delete(self, predicate, by='key'):
        data = deepcopy(self._data)
        if by not in ['key', 'value', 'key+value']:
            msg = f'Invalid by argument: {by}. Needs to be one of: '
            msg += 'key, value, key+value.'
            raise ValueError(msg)

        for key, val in self._data.items():
            item = None
            if by == 'key':
                item = key
            elif by == 'value':
                item = val
            else:
                item = [key, val]

            if predicate(item):
                del data[key]

        self._data = data
        return self

    def set(
        self,
        predicate=None,
        key_setter=None,
        value_setter=None,
        by='key'
    ):
        if by not in ['key', 'value', 'key+value']:
            msg = f'Invalid by argument: {by}. Needs to be one of: '
            msg += 'key, value, key+value.'
            raise ValueError(msg)

        if predicate is None:
            predicate = lambda x: x

        if key_setter is None:
            key_setter = lambda x: x

        if value_setter is None:
            value_setter = lambda x: x

        data = deepcopy(self._data)
        for key, val in self._data.items():
            item = None
            if by == 'key':
                item = key
            elif by == 'value':
                item = val
            else:
                item = [key, val]

            if predicate(item):
                k = key_setter(key)
                v = value_setter(val)
                del data[key]
                data[k] = v

        self._data = data
        return self

    def update(self, dict_):
        data = tools.flatten(dict_, separator=self._separator, embed_types=True)
        self._data.update(data)
        return self

    def to_networkx_graph(self):
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
                    graph.add_node(v, short_name=name, node_type='value')
                    graph.add_edge(k, v)

        recurse(tools.nest(self._data), 'root')
        graph.remove_node('root')
        return graph

    def to_dot_graph(self, orthogonal_edges=False, color_scheme=None):
        if color_scheme is None:
            color_scheme = tools.COLOR_SCHEME

        graph = self.to_networkx_graph()
        dot = networkx.drawing.nx_pydot.to_pydot(graph)

        dot.set_bgcolor(color_scheme['background'])
        if orthogonal_edges:
            dot.set_splines('ortho')

        for node in dot.get_nodes():
            node.set_shape('rect')
            node.set_style('filled')
            node.set_color(color_scheme['node'])
            node.set_fillcolor(color_scheme['node'])
            node.set_fontcolor(color_scheme['node_fontcolor'])
            node.set_fontname('Courier')

            attrs = node.get_attributes()
            if 'short_name' in attrs:
                node.set_label(attrs['short_name'])
            if 'node_type' in attrs and attrs['node_type'] == 'value':
                node.set_color(color_scheme['node_value'])
                node.set_fillcolor(color_scheme['node_value'])
                node.set_fontcolor(color_scheme['node_value_fontcolor'])

        for edge in dot.get_edges():
            edge.set_color(color_scheme['edge'])

            node = dot.get_node(edge.get_destination())[0]
            attrs = node.get_attributes()
            if 'node_type' in attrs and attrs['node_type'] == 'value':
                edge.set_color(color_scheme['edge_value_color'])

        return dot

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

        tools.write_dot_graph(
            fullpath,
            layout=layout,
            orthogonal_edges=orthogonal_edges,
            color_scheme=color_scheme,
        )
        return self
