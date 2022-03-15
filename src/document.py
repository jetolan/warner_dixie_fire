import os
import shutil
import subprocess


def make_document(figdir):
    texpath = f'{figdir}/document.tex'
    shutil.copy('document.tex', texpath)
    cwd = os.getcwd()
    os.chdir(figdir)
    cmd = ['pdflatex', 'document.tex', '-output-directory', '../../doc/']
    call = subprocess.run(cmd,
                          stdout=subprocess.PIPE,
                          text=True)
    apn = os.path.basename(figdir)
    docdir = '../../doc/'
    if not os.path.exists(docdir):
        os.makedirs(docdir)
    shutil.copy('document.pdf', f'{docdir}/{apn}.pdf')
    os.chdir(cwd)
    return texpath


if __name__ == "__main__":
    figdir = '../fig/011180014'
    make_document(figdir)
