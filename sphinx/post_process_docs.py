import os
from pathlib import Path
import re
# ------------------------------------------------------------------------------


def insert_coverage_report_link(target, coverage_path):
    with open(target) as f:
        html = f.readlines()

    output = ''
    flag = False
    for line in html:
        # line = line.decode('utf-8')
        regex = '.*<div class="toctree-wrapper compound">.*'
        if re.search(regex, line) and not flag:
            output += '<p><a href="{}">CODE COVERAGE</a></p>\n'\
                .format(coverage_path)
            output += line
            flag = True
        else:
            output += line

    os.remove(target)
    with open(target, 'w') as f:
        f.write(output)


def main():
    target = Path(Path(__file__).parents[1], 'docs/index.html')\
        .absolute().as_posix()
    insert_coverage_report_link(target, 'htmlcov/index.html')


if __name__ == '__main__':
    main()
