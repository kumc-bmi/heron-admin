from collections import namedtuple
import ast

from ocap_file import Path


def main(stdin, cwd):
    deps = [
        ModDep(ModInfo(d1, p1), ModInfo(d2, p2))
        for line in stdin
        for ((d1, p1), (d2, p2)) in [ast.literal_eval(line)]
    ]
    for depth, item, prog in mod_tree(deps, ROOT, cwd):
        print('  ' * depth + str(item) + ('*' if prog else ''))


def mod_tree(deps, root, fs):
    bySuper = {super: sorted(sub for (ss, sub) in deps
                             if ss == super and sub.mod_path)
               for (super, _) in deps}
    seen = set()

    def visit(m, depth):
        if m in seen:
            return
        seen.add(m)
        yield depth, m, '__main__' in m.source(fs)
        for sub in bySuper[m]:
            for out in visit(sub, depth + 1):
                yield out

    for out in visit(root, 0):
        yield out


class ModInfo(namedtuple('ModInfo', ['pkg_dir', 'mod_path'])):
    def __repr__(self):
        if self.mod_path is None:
            return '?'
        return self.mod_path.replace('.py', '').replace('/', '.')

    def source(self, fs):
        path = fs / self.pkg_dir / self.mod_path
        if not str(path).endswith('.py'):
            path = path / '__init__.py'
        return path.open(mode='r').read()


ROOT = ModInfo('/home/dconnolly/projects/heron-admin', 'heron_wsgi/heron_srv.py')


class ModDep(namedtuple('ModDep', ['super', 'sub'])):
    pass


if __name__ == '__main__':
    def _script():
        from sys import stdin
        from io import open as io_open
        from os.path import join as joinpath

        cwd = Path('.', open=io_open, joinpath=joinpath)
        main(stdin, cwd)

    _script()
