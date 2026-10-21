"""Import a LaTeX paper and referenced local resources without modifying the original."""
from pathlib import Path
import argparse, shutil, re
HOME=Path(__file__).resolve().parent

def import_project(path,workspace):
 path=Path(path).resolve(); workspace=Path(workspace).resolve()
 if not path.is_file() or path.suffix.lower()!='.tex':raise ValueError('Choose an existing .tex file')
 src=path.parent
 workspace.mkdir(parents=True,exist_ok=True)
 target=workspace/'original.tex'
 if target.exists():raise FileExistsError('workspace/original.tex exists: preserve old paper and choose a clean workspace')
 for file in src.rglob('*'):
  if not file.is_file():continue
  rel=file.relative_to(src)
  if any(x in rel.parts for x in ('.git','build','output','.venv')):continue
  if file.suffix.lower() not in ('.tex','.bib','.png','.pdf','.jpg','.jpeg','.eps','.svg','.sty','.cls'):continue
  # Keep source-relative paths for includegraphics and input.
  dest=workspace/rel
  dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():shutil.copy2(file,dest)
 shutil.copy2(path,target)
 print('Imported original:',target)
 print('Copied source assets. Existing files were not overwritten.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('tex_file');p.add_argument('--workspace',default=str(HOME/'workspace'))
 a=p.parse_args();import_project(a.tex_file,a.workspace)
