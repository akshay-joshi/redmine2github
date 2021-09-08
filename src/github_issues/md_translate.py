from collections import OrderedDict
import re


def get_translate_dict():
    d = OrderedDict()
    for hlevel in range(1, 7):
        d['h%s.' % hlevel] = '#' * hlevel        # e.g. d['h2.'] = '##'
    d['\n# '] = '\n1. '  # lists
    d['<pre>'] = '```'  # code block
    d['</pre>'] = '\n```'  # code block
    d['commit:#{gitID}'] = 'commit:#{gitID}'
    d['commit:...'] = 'commit:...'
    d['commit:\n'] = 'commit:\n'
    d['commit:sha_code'] = 'commit:sha_code'
    d['commit: '] = 'commit: '
    d['commit:qgis|'] = ''
    d['commit:'] = ''
    return d


def translate_for_github(content):
    if not content:
        return None

    for k, v in get_translate_dict().items():
        content = content.replace(k, v)

    # search images
    matches = re.findall(r'(!>?(https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*))(\([\w\s\d,\-_.]+\))?!:?(?:https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*))?)', content)
    for match in matches:
        title = match[2] if match[2] else "image"
        repl = '![' + title + '](' + match[1] + ')'
        content = re.sub(match[0], repl, content)

    return content
