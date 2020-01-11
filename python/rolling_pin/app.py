from flask import Flask, Response, request, redirect, url_for
from flasgger import Swagger

from rolling_pin.blob_etl import BlobETL
# ------------------------------------------------------------------------------


app = Flask(__name__)
swagger = Swagger(app)


@app.route('/')
def index():
    return redirect(url_for('flasgger.apidocs'))


@app.route('/to_svg')
def to_svg():
    '''
    Converts a given JSON blob into a SVG graph.
    ---
    parameters:
      - name: to_svg
        type: object
        required: true
    responses:
      200:
        description: A SVG image.
        examples:
            blob: {'foo': {'bar': 'baz'}}
    '''
    blob = request.get_json()
    content = BlobETL(blob)\
        .to_dot_graph()\
        .create_svg()\
        .decode('utf-8')
    return Response(content, mimetype='image/svg+xml')


app.run(debug=True, host='0.0.0.0')
