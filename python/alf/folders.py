# -*- coding:utf-8 -*-
# @Author: Niccolò Bonacchi
# @Date: Monday, January 21st 2019, 6:28:49 pm
# @Last Modified by: Niccolò Bonacchi
# @Last Modified time: 21-01-2019 06:28:51.5151
from pathlib import Path
from typing import List, Union
import logging

import ibllib.time

log = logging.getLogger('ibllib')


def subjects_data_folder(folder: Path) -> Path:
    """Given a root_data_folder will try to find a 'Subjects' data folder.
    If Subjects folder is passed will return it directly."""
    # Try to find Subjects folder one level
    if folder.name.lower() != 'subjects':
        # Try to find Subjects folder if folder.glob
        spath = [x for x in folder.glob('*') if x.name.lower() == 'subjects']
        if not spath:
            raise(ValueError)
        elif len(spath) > 1:
            raise(ValueError)
        else:
            folder = folder / spath[0]

    return folder


def remove_empty_folders(folder: Union[str, Path]) -> None:
    """Will iteratively remove any children empty folders"""
    all_folders = [x for x in Path(folder).rglob('*') if x.is_dir()]
    for f in all_folders:
        try:
            f.rmdir()
        except Exception:
            continue


def find_sessions(folder: Union[str, Path]) -> List[Path]:
    # Ensure folder is a Path object
    if not isinstance(folder, Path):
        folder = Path(folder)
    out = [x.parent.parent for x in folder.rglob('_iblrig_taskSettings.raw*')]
    return out


def find_subject_names(folder: Union[str, Path]) -> List[Path]:
    # Ensure folder is a Path object
    if not isinstance(folder, Path):
        folder = Path(folder)
    out = [x.parent.parent.parent.parent.name
           for x in folder.rglob('_iblrig_taskSettings.raw*')]
    return out


def _isdatetime(s: str) -> bool:
    try:
        ibllib.time.isostr2date(s)
        return True
    except Exception:
        return False


def session_path(path: Union[str, Path]) -> str:
    path = Path(path)
    sess = None
    for i, p in enumerate(path.parts):
        if p.isdigit() and _isdatetime(path.parts[i - 1]):
            sess = str(Path().joinpath(*path.parts[:i + 1]))

    return sess
