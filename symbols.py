
from model import *
from config import symbol_url

import urllib2 as urllib
import re
import fileinput

class Symbol():

    def __init__(self):
        self.symboldb = SymbolDB()

    def _add_build(self, m):
        try:
            new = Build(os=m.group(1), arch=m.group(2), debug_id=m.group(3), name=m.group(4))
            self.symboldb.session.add(new)
            self.symboldb.session.commit()
        except ProgrammingError, e:
            print e
            return None
        return(new.id)

    def _add_module(self, m):
        try:
            new = Module(os=m.group(1), arch=m.group(2), debug_id=m.group(3), name=m.group(4))
            self.symboldb.session.add(new)
            self.symboldb.session.commit()
        except ProgrammingError, e:
            print e
            return None
        return(new.id)


    def _add_files(self, files, module):
        try:
            self.symboldb.session.add_all(File(number=f[0],
                                               name=f[1],
                                               module=module) for f in files)
        except ProgrammingError, e:
            print e

    def _add_publics(self, publics, module):
        try:
            self.symboldb.session.add_all(Public(address=p[0],
                                                 size=p[1], name=p[2],
                                                 module=module) for p in publics)
        except ProgrammingError, e:
            print e

    def _add_funcs(self, funcs, module):
        try:
            gen = (Function(address=f[0],
                            size=f[1],
                            parameter_size=f[2],
                            name=f[3],
                            module=module,
                            address_range="[%d, %d)" % (f[0], f[0] + f[1])
                            ) for f in funcs)
            self.symboldb.session.add_all(gen)
        except ProgrammingError, e:
            print e

    def _add_lines(self, lines, module):
        try:
            gen = (Line(address=l[0],
                        size=l[1],
                        line=l[2],
                        file=l[3],
                        module=module,
                        address_range="[%d, %d)" % (l[0], l[0] + l[1]))
                   for l in lines)
            self.symboldb.session.add_all(gen)
        except ProgrammingError, e:
            print e

    def _add_stacks(self, stacks, module):
        try:
            gen = (Stackwalk(address=s[0],
                             stackwalk_data=s[1],
                             module=module) for s in stacks)
            self.symboldb.session.add_all(gen)
        except ProgrammingError, e:
            print e

    def add(self, url):
        page = urllib.urlopen(url)
        symbols = page.read().split('\n')
        page.close()
        module = None
        mod_id = None
        skip = 0
        files = []
        funcs = []
        publics = []
        stacks = []
        lines = []

        for line in symbols:
            if line is None:
                break

            m = re.search('^MODULE (\S+) (\S+) (\S+) (\S+)', line)
            if m:
                module = self.symboldb.session.query(Module.id).filter_by(debug_id=m.group(3), name=m.group(4)).first()
                if module:
                    skip = 1
                    break

                mod_id = self._add_module(m)
                continue

            m = re.search('^FILE (\S+) (.*)', line)
            if m:
                files.append((m.group(1), m.group(2)))
                continue

            m = re.search('^FUNC (\S+) (\S+) (\S+) (\S+)', line)
            if m:
                funcs.append((int(m.group(1), 16), int(m.group(2), 16),
                              int(m.group(3), 16), m.group(4)))
                continue

            # XXX Figure out how to handle ranges for stacks, also non WIN stacks
            m = re.search('^STACK WIN (\S+) (\S+) (\S+) (.*)', line)
            if m:
                stacks.append((int(m.group(2), 16), m.group(0)))
                continue

            # XXX
            m = re.search('^PUBLIC (\S+) (\S+) (\S+)', line)
            if m:
                publics.append((int(m.group(1), 16), int(m.group(2), 16),
                                m.group(3)))
                continue

            m = re.search('^(\S+) (\S+) (\S+) (\S+)', line)
            if m:
                lines.append((int(m.group(1), 16), int(m.group(2), 16),
                              int(m.group(3)), int(m.group(4))))
                continue
        # Now add all the collected data
        self._add_files(files, mod_id)
        self._add_funcs(funcs, mod_id)
        #self._add_publics(publics, mod_id)
        self._add_lines(lines, mod_id)
        self._add_stacks(stacks, mod_id)

        self.symboldb.session.commit()

    def remove(self, debug_id, name):
        pass

if __name__ == "__main__":
    test = Symbol()

    import glob
    urls = []
    for line in fileinput.input():
        line = line.rstrip()
        if not line.endswith(".sym"):
            continue
        urls.append(line)

    print len(urls)
    for url in urls:
        #if re.search('js.pdb', url):
        print "Adding %s" % url
        test.add(symbol_url + url)

