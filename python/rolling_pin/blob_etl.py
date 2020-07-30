from typing import Any, Callable, Dict, Iterator, List, Optional, Union
from IPython.display import HTML, Image
import pydot

from collections import Counter
import json
import os
import re
from copy import deepcopy
from pathlib import Path

import lunchbox.tools as lbt
from pandas import DataFrame
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
        # type: (Any, str) -> None
        '''
        Contructs BlobETL instance.

        Args:
            blob (object): Iterable object.
            separator (str, optional): String to be used as a field separator in
                each key. Default: '/'.
        '''
        self._data = tools \
            .flatten(blob, separator=separator, embed_types=True)  # type: Dict[str, Any]
        self._separator = separator  # type: str

    # EDIT_METHODS--------------------------------------------------------------
    def query(self, regex, ignore_case=True):
        # type: (str, bool) -> BlobETL
        '''
        Filter data items by key according to given regular expression.

        Args:
            regex (str): Regular expression.
            ignore_casd (bool, optional): Whether to consider case in the
                regular expression search. Default: False.

        Returns:
            BlobETL: New BlobETL instance.
        '''
        if ignore_case:
            return self.filter(lambda x: bool(re.search(regex, x, re.I)), by='key')
        return self.filter(lambda x: bool(re.search(regex, x)), by='key')

    def filter(self, predicate, by='key'):
        # type: (Callable[[Any], bool], str) -> BlobETL
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

        return BlobETL(data, separator=self._separator)

    def delete(self, predicate, by='key'):
        # type: (Callable[[Any], bool], str) -> BlobETL
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

        return BlobETL(data, separator=self._separator)

    def set(
        self,
        predicate=None,  # type: Optional[Callable[[Any, Any], bool]]
        key_setter=None,  # type: Optional[Callable[[Any, Any], str]]
        value_setter=None,  # type: Optional[Callable[[Any, Any], Any]]
    ):
        # type: (...) -> BlobETL
        '''
        Filter data items by key, value or key + value, according to a given
        predicate. Then set that items key by a given function and value by a
        given function.

        Args:
            predicate (function, optional): Function of the form:
                lambda k, v: bool. Default: None --> lambda k, v: True.
            key_setter (function, optional): Function of the form:
                lambda k, v: str. Default: None --> lambda k, v: k.
            value_setter (function, optional):  Function of the form:
                lambda k, v: object. Default: None --> lambda k, v: v.

        Returns:
            BlobETL: New BlobETL instance.
        '''
        # assign default predicate
        if predicate is None:
            predicate = lambda k, v: True

        # assign default key_setter
        if key_setter is None:
            key_setter = lambda k, v: k

        # assign default value_setter
        if value_setter is None:
            value_setter = lambda k, v: v

        data = deepcopy(self._data)
        for item in self._data.items():
            if predicate(*item):
                k = key_setter(*item)
                v = value_setter(*item)
                del data[item[0]]
                data[k] = v

        return BlobETL(data, separator=self._separator)

    def update(self, item):
        # type: (Union[Dict, BlobETL]) -> BlobETL
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
        return BlobETL(data, separator=self._separator)

    def set_field(self, index, field_setter):
        # type: (int, Callable[[str], str]) -> BlobETL
        '''
        Set's a field at a given index according to a given function.

        Args:
            index (int): Field index.
            field_setter (function): Function of form lambda str: str.

        Returns:
            BlobETL: New BlobETL instance.
        '''
        output = {}
        for key, val in self._data.items():
            fields = key.split(self._separator)
            fields[index] = field_setter(fields[index])
            key = self._separator.join(fields)
            output[key] = val
        return BlobETL(output, separator=self._separator)

    # EXPORT-METHODS------------------------------------------------------------
    def to_dict(self):
        # type: () -> Dict[str, Any]
        '''
        Returns:
            dict: Nested representation of internal data.
        '''
        return tools.unembed(
            tools.nest(deepcopy(self._data), separator=self._separator)
        )

    def to_flat_dict(self):
        # type: () -> Dict[str, Any]
        '''
        Returns:
            dict: Flat dictionary with embedded types.
        '''
        return deepcopy(self._data)

    def to_records(self):
        # type: () -> List[Dict]
        '''
        Returns:
            list[dict]: Data in records format.
        '''
        data = []
        for key, val in self._data.items():
            fields = key.split(self._separator)
            row = {i: v for i, v in enumerate(fields)}  # type: Dict[Any, Any]
            row['value'] = val
            data.append(row)
        return data

    def to_dataframe(self, group_by=None):
        # type: (Optional[int]) -> DataFrame
        '''
        Convert data to pandas DataFrame.

        Args:
            group_by (int, optional): Field index to group rows of data by.
                Default: None.

        Returns:
            DataFrame: DataFrame.
        '''
        data = self.to_records()  # type: Any
        data = DataFrame(data)

        if group_by is not None:
            group = list(range(0, group_by))
            data = DataFrame(data)\
                .groupby(group, as_index=False)\
                .agg(lambda x: x.tolist())\
                .apply(lambda x: x.to_dict(), axis=1)\
                .tolist()
            data = DataFrame(data)

        # clean up column order
        cols = data.columns.tolist()  # type: List[str]
        cols = list(sorted(filter(lambda x: x != 'value', cols)))
        cols += ['value']
        data = data[cols]

        return data

    def to_prototype(self):
        # type: () -> BlobETL
        '''
        Convert data to prototypical representation.

        Example:

        >>> data = {
        'users': [
                {
                    'name': {
                        'first': 'tom',
                        'last': 'smith',
                    }
                },{
                    'name': {
                        'first': 'dick',
                        'last': 'smith',
                    }
                },{
                    'name': {
                        'first': 'jane',
                        'last': 'doe',
                    }
                },
            ]
        }
        >>> BlobETL(data).to_prototype().to_dict()
        {
            '^users': {
                '<list_[0-9]+>': {
                    'name': {
                        'first$': Counter({'dick': 1, 'jane': 1, 'tom': 1}),
                        'last$': Counter({'doe': 1, 'smith': 2})
                    }
                }
            }
        }

        Returns:
            BlobETL: New BlobETL instance.
        '''
        def regex_in_list(regex, items):
            # type: (str, List[str]) -> bool
            for item in items:
                if re.search(regex, item):
                    return True
            return False  # pragma: no cover

        def field_combinations(a, b):
            # type: (List[str], List[str]) -> List[str]
            output = []
            for fa in a:
                for fb in b:
                    output.append(fa + self._separator + fb)
            return output

        keys = list(self._data.keys())
        fields = list(map(lambda x: x.split(self._separator), keys))

        fields = DataFrame(fields)\
            .apply(lambda x: x.unique().tolist())\
            .apply(lambda x: filter(lambda y: y is not None, x)) \
            .apply(lambda x: map(
                lambda y: re.sub(r'<([a-z]+)_\d+>', '<\\1_[0-9]+>', y),
                x)) \
            .apply(lambda x: list(set(x))) \
            .tolist()

        prev = fields[0]
        regexes = list()
        for i, level in enumerate(fields[1:]):
            temp = field_combinations(prev, level)  # type: Union[List, Iterator]
            temp = filter(lambda x: regex_in_list('^' + x, keys), temp)
            prev = list(temp)
            regexes.extend(prev)

        regexes = lbt.get_ordered_unique(regexes)

        p_keys = set()
        for regex in regexes:
            other = deepcopy(regexes)
            other.remove(regex)
            not_in_other = True
            for item in other:
                if regex in item:
                    not_in_other = False
            if not_in_other:
                p_keys.add(f'^{regex}$')

        output = {}
        for key in p_keys:
            values = self.query(key).to_flat_dict().values()
            output[key] = Counter(values)
        return BlobETL(output, separator=self._separator)

    def to_networkx_graph(self):
        # type: () -> networkx.DiGraph
        '''
        Converts internal dictionary into a networkx directed graph.

        Returns:
            networkx.DiGraph: Graph representation of dictionary.
        '''
        graph = networkx.DiGraph()
        graph.add_node('root')
        embed_re = re.compile(r'<[a-z]+_(\d+)>')

        def recurse(item, parent):
            # type: (Dict, str) -> None
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

        recurse(tools.nest(self._data, self._separator), 'root')
        graph.remove_node('root')
        return graph

    def to_dot_graph(
        self, orthogonal_edges=False, orient='tb', color_scheme=None
    ):
        # type: (bool, str, Optional[Dict[str, str]]) -> pydot.Dot
        '''
        Converts internal dictionary into pydot graph.
        Key and value nodes and edges are colored differently.

        Args:
            orthogonal_edges (bool, optional): Whether graph edges should have
                non-right angles. Default: False.
            orient (str, optional): Graph layout orientation. Default: tb.
                Options include:

                * tb - top to bottom
                * bt - bottom to top
                * lr - left to right
                * rl - right to left
            color_scheme: (dict, optional): Color scheme to be applied to graph.
                Default: rolling_pin.tools.COLOR_SCHEME

        Raises:
            ValueError: If orient is invalid.

        Returns:
            pydot.Dot: Dot graph representation of dictionary.
        '''
        orient = orient.lower()
        orientations = ['tb', 'bt', 'lr', 'rl']
        if orient not in orientations:
            msg = f'Invalid orient value. {orient} not in {orientations}.'
            raise ValueError(msg)

        # set default colort scheme
        if color_scheme is None:
            color_scheme = tools.COLOR_SCHEME

        # create pydot graph
        graph = self.to_networkx_graph()
        dot = networkx.drawing.nx_pydot.to_pydot(graph)

        # set layout orientation
        dot.set_rankdir(orient.upper())

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
        orient='tb',
        color_scheme=None,
        as_png=False,
    ):
        # type: (str, bool, str, Optional[Dict[str, str]], bool) -> Union[Image, HTML]
        '''
        For use in inline rendering of graph data in Jupyter Lab.

        Args:
            layout (str, optional): Graph layout style.
                Options include: circo, dot, fdp, neato, sfdp, twopi.
                Default: dot.
            orthogonal_edges (bool, optional): Whether graph edges should have
                non-right angles. Default: False.
            orient (str, optional): Graph layout orientation. Default: tb.
                Options include:

                * tb - top to bottom
                * bt - bottom to top
                * lr - left to right
                * rl - right to left
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
            orient=orient,
            color_scheme=color_scheme,
        )
        return tools.dot_to_html(dot, layout=layout, as_png=as_png)

    def write(
        self,
        fullpath,
        layout='dot',
        orthogonal_edges=False,
        orient='tb',
        color_scheme=None
    ):
        # type: (Union[str, Path], str, bool, str, Dict[str, str]) -> BlobETL
        '''
        Writes internal dictionary to a given filepath.
        Formats supported: svg, dot, png, json.

        Args:
            fulllpath (str or Path): File tobe written to.
            layout (str, optional): Graph layout style.
                Options include: circo, dot, fdp, neato, sfdp, twopi.
                Default: dot.
            orthogonal_edges (bool, optional): Whether graph edges should have
                non-right angles. Default: False.
            orient (str, optional): Graph layout orientation. Default: tb.
                Options include:

                * tb - top to bottom
                * bt - bottom to top
                * lr - left to right
                * rl - right to left
            color_scheme: (dict, optional): Color scheme to be applied to graph.
                Default: rolling_pin.tools.COLOR_SCHEME

        Raises:
            ValueError: If invalid file extension given.

        Returns:
            BlobETL: self.
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
            orient=orient,
            color_scheme=color_scheme,
        )
        try:
            tools.write_dot_graph(graph, fullpath, layout=layout,)
        except ValueError:
            msg = f'Invalid extension found: {ext}. '
            msg += 'Valid extensions include: svg, dot, png, json.'
            raise ValueError(msg)
        return self
