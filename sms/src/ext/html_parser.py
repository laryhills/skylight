import sys
import os
from io import StringIO


def strip_head(fd):
    data = ''
    while True:
        data += fd.read(1)
        if data[-7:] == '</head>':
            break
    data = data[data.find('<head>'):]
    return data


def strip_div_sections(fd):
    div_sections = []
    keyword = '<div class=WordSection'
    curr_section = ''
    while True:
        char = fd.read(1)
        if not char: break
        if curr_section[-1 * (len(keyword) - 1):] + char == keyword:
            curr_section = curr_section[:-1 * len(keyword)]
            div_sections.append(curr_section)
            curr_section = keyword
        else: curr_section += char

    # Strips out the closing body and html tags
    idx = curr_section.rfind('</div>')
    curr_section = curr_section[: idx + 6]
    div_sections.append(curr_section)

    # Strips out the opening body tag
    first_div_section = div_sections[0]
    idx = first_div_section.find('<div>')
    div_sections[0] = first_div_section[idx:]

    # Combines the first 2 div sections
    div_sections[0] += div_sections[1]
    div_sections.pop(1)
    
    return div_sections


html_fmt = '''<html>
    {head}
    <body lang=EN-US>
        {div_section}
    </body>
</html>
'''


def split_html(html):
    htmls = []
    with StringIO(html) as fd:
        head = strip_head(fd)
        div_sections = strip_div_sections(fd)
        for div_section in div_sections:
            data = html_fmt.format(head=head, div_section=div_section)
            htmls.append(data)

    return htmls


if __name__ == '__main__':
    with open(sys.argv[1]) as fd:
        fname, ext = os.path.splitext(sys.argv[1])
        head = strip_head(fd)
        div_sections = strip_div_sections(fd)
        for idx, div_section in enumerate(div_sections):
            data = html_fmt.format(head=head, div_section=div_section)
            n_fname = fname + '_' + str(idx) + ext
            with open(n_fname, 'w') as f:
                f.write(data)
