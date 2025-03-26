{ pkgs }: {
  deps = [
    pkgs.tk
    pkgs.tcl
    pkgs.qhull
    pkgs.pkg-config
    pkgs.gtk3
    pkgs.gobject-introspection
    pkgs.ghostscript
    pkgs.freetype
    pkgs.ffmpeg-full
    pkgs.cairo
    pkgs.glibcLocales
    pkgs.python312
    pkgs.python312Packages.flask
    pkgs.python312Packages.pip
    pkgs.python312Packages.numpy
    pkgs.python312Packages.pandas
  ];
} 