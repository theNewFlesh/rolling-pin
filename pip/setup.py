from distutils.core import setup
setup(
    name='rolling-pin',
    packages=['rolling_pin'],
    version='0.2.1',
    license='MIT',
    description='A library of generic tools for ETL work and visualization of JSON blobs and python repositories.',  # noqa E501
    author='Alex Braun',
    author_email='Alexander.G.Braun@gmail.com',
    url='https://github.com/theNewFlesh/rolling-pin',
    download_url='https://github.com/theNewFlesh/rolling-pin/archive/0.2.1.tar.gz',
    keywords=['ETL', 'blob', 'dependency', 'graph', 'svg', 'networkx', 'transform'],
    install_requires=[
        'graphviz',
        'ipython',
        'networkx',
        'numpy',
        'pandas',
        'pydot',
    ],
    classifiers=[
      'Development Status :: 4 - Beta',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Programming Language :: Python :: 3',
      'Programming Language :: Python :: 3.7',
    ],
)
