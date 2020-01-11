from flask import Flask, Response, request, redirect, url_for, jsonify
from flasgger import Swagger

from rolling_pin.blob_etl import BlobETL
# ------------------------------------------------------------------------------


app = Flask(__name__)
swagger = Swagger(app)


@app.route('/')
def index():
    return redirect(url_for('flasgger.apidocs'))


def get_svg(request):
    data = request['data']

    params = dict(
        layout='dot',
        orthogonal_edges=False,
        orient='tb',
        color_scheme=None,
    )
    if 'parameters' in request:
        params.update(request['parameters'])

    content = BlobETL(data)\
        .to_dot_graph(
            orthogonal_edges=params['orthogonal_edges'],
            orient=params['orient'],
            color_scheme=params['color_scheme'],
        )\
        .create_svg(prog=params['layout'])\
        .decode('utf-8')
    return Response(content, mimetype='image/svg+xml')


@app.route('/to_svg')
def to_svg():
    '''
    Converts a given JSON blob into a SVG graph.
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
        type: bool
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
        default: rolling_pin.tools.COLOR_SCHEME

    responses:
      200:
        description: A SVG image.
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
        req = request.get_json()
        return get_svg(req)
    except Exception as e:
        msg = e.__class__.__name__ + ': ' + ' '.join(e.args)
        return jsonify(error=msg, status=400, success=False)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
