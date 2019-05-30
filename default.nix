# nix + direnv + emacs + mypy + python2 seems a bridge too far.
# See .envrc for pipenv usage

with import <nixpkgs> {};
stdenv.mkDerivation {
  name = "env";
  buildInputs = [
    direnv
    emacs
    # python27Packages.virtualenv
    # python27Packages.tox
    python27Packages.flake8
    python37Packages.mypy
  ];
}
