from typing import Any, Dict, Optional

from flask import Flask, Response, request, redirect, url_for
from flasgger import Swagger, swag_from
import lunchbox.tools as lbt

from rolling_pin.blob_etl import BlobETL
# ------------------------------------------------------------------------------


'''
Rolling-Pin Flask service.
'''


app = Flask(__name__)
swagger = Swagger(app)


@app.route('/')
def index():
    # type: () -> Any
    return redirect(url_for('flasgger.apidocs'))


@lbt.api_function
def get_svg(
    data='<required>',
    layout='dot',
    orthogonal_edges=False,
    orient='tb',
    color_scheme=None,
):
    # type: (str, str, bool, str, Optional[Dict]) -> str
    '''
    Generate a SVG string from a given JSON blob.

    Args:
        data (dict or list): JSON blob.
        layout (str, optional): Graph layout style.
            Options include: circo, dot, fdp, neato, sfdp, twopi. Default: dot.
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

    Returns:
        str: SVG string.
    '''
    output = BlobETL(data)\
        .to_dot_graph(
            orthogonal_edges=orthogonal_edges,
            orient=orient,
            color_scheme=color_scheme)\
        .create_svg(prog=layout)\
        .decode('utf-8')
    return output


@app.route('/to_svg')
@swag_from(dict(
    parameters=[
        dict(
            name='data',
            type='object',
            required=True,
        ),
        dict(
            name='layout',
            type='string',
            description='Graph layout style.',
            enum=['circo', 'dot', 'fdp', 'neato', 'sfdp', 'twopi'],
            required=False,
            default='dot',
        ),
        dict(
            name='orthogonal_edges',
            type='boolean',
            required=False,
            description='Whether graph edges should have non-right angles.',
            default=False,
        ),
        dict(
            name='orient',
            type='string',
            required=False,
            description='Graph layout orientation.',
            default='tb',
            enum=['tb', 'bt', 'lr', 'rl'],
        ),
        dict(
            name='color_scheme',
            type='object',
            required=False,
            description='Color scheme to be applied to graph.',
            default='none',
        )
    ],
    responses={
        200: dict(
            description='A SVG image.',
            content='image/svg+xml',
        ),
        400: dict(
            description='Invalid JSON request sent.',
            example=dict(
                error="KeyError: data",
                status=400,
                success=False,
            )
        )
    }
))
def to_svg():
    # type: () -> Response
    '''
    Endpoint for converting a given JSON blob into a SVG graph.
    '''
    try:
        params = request.get_json()
        return Response(get_svg(**params), mimetype='image/svg+xml')
    except Exception as e:
        msg = e.__class__.__name__ + ': ' + ' '.join(e.args)
        return Response(msg, status=400)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
