from flask import Flask, Response, request, redirect, url_for, jsonify
from flasgger import Swagger

from rolling_pin.blob_etl import BlobETL
import rolling_pin.utils as utils
# ------------------------------------------------------------------------------


app = Flask(__name__)
swagger = Swagger(app)


@app.route('/')
def index():
    return redirect(url_for('flasgger.apidocs'))


@utils.api_function
def get_svg(
    data='<required>',
    layout='dot',
    orthogonal_edges=False,
    orient='tb',
    color_scheme=None,
):
    output = BlobETL(data)\
        .to_dot_graph(
            orthogonal_edges=orthogonal_edges,
            orient=orient,
            color_scheme=color_scheme)\
        .create_svg(prog=layout)\
        .decode('utf-8')
    return output


@app.route('/to_svg')
def to_svg():
    '''
    Endpoint for converting a given JSON blob into a SVG graph.
    ---
    parameters:
      - name: data
        type: object
        required: true
      - name: layout
        type: string
        description: Graph layout style.
        enum: ['circo', 'dot', 'fdp', 'neato', 'sfdp', 'twopi']
        required: false
        default: dot
      - name: orthogonal_edges
        type: boolean
        required: false
        description: Whether graph edges should have non-right angles.
        default: false
      - name: orient
        type: string
        required: false
        description: Graph layout orientation.
        default: tb
        enum: ['tb', 'bt', 'lr', 'rl']
      - name: color_scheme
        type: object
        required: false
        description: Color scheme to be applied to graph.
        default: none

    responses:
      200:
        description: A SVG image.
        content:
          image/svg+xml:
      400:
        description: Invalid JSON request sent.
        example:
            {
                "error": "KeyError: data",
                "status": 400,
                "success": false
            }
    '''
    try:
        params = request.get_json()
        return Response(get_svg(**params), mimetype='image/svg+xml')
    except Exception as e:
        msg = e.__class__.__name__ + ': ' + ' '.join(e.args)
        return jsonify(error=msg, status=400, success=False)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
